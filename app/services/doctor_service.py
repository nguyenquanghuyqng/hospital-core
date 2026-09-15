"""
Doctor Service — Application Service layer cho bác sĩ.

Chứa toàn bộ business logic liên quan đến hàng đợi và quy trình khám của bác sĩ.
Tầng này nằm giữa API (controller) và CRUD (data access):

    API (doctor.py) → DoctorService → CRUDReception → DB

Nguyên tắc:
- Không import FastAPI (HTTPException được raise tại đây để giữ đơn giản,
  nhưng logic xử lý data hoàn toàn độc lập với HTTP).
- Không thực hiện ``db.commit()`` — commit được ủy quyền cho ``get_db`` dependency.
- Mỗi method là một use-case rõ ràng.
"""
import logging
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.reception import Reception
from app.models.patient import Patient
from app.models.enums import ReceptionStatus, VisitStatus
from sqlalchemy import or_
from app.schemas.doctor import QueueStatsResponse, TransferRequest, VisitStatusUpdate
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)


class DoctorService:
    """
    Application Service tập trung toàn bộ business logic của bác sĩ.

    Được inject vào endpoints thông qua singleton ``doctor_service``.
    Mỗi method nhận ``AsyncSession`` từ endpoint để tham gia cùng transaction.
    """

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def resolve_clinic_room(
        clinic_room_param: Optional[str],
        user_clinic_room: Optional[str],
    ) -> Optional[str]:
        """
        Xác định phòng khám từ param hoặc user profile.

        Ưu tiên param truyền vào; fallback về ``clinic_room`` của user.
        Trả ``None`` nếu cả hai đều trống — dành cho admin xem tất cả phòng.
        """
        return clinic_room_param or user_clinic_room or None

    @staticmethod
    async def _get_reception_or_404(db: AsyncSession, reception_id: int) -> Reception:
        """
        Lấy lượt tiếp đón kèm eager-load patient hoặc raise 404.

        Args:
            db: Async database session.
            reception_id: ID lượt tiếp đón cần lấy.

        Returns:
            :class:`~app.models.reception.Reception` với ``patient`` đã load.

        Raises:
            HTTPException 404: Không tìm thấy lượt tiếp đón.
        """
        result = await db.execute(
            select(Reception)
            .options(selectinload(Reception.patient))
            .where(Reception.id == reception_id)
        )
        reception = result.scalar_one_or_none()
        if not reception:
            raise HTTPException(status_code=404, detail="Không tìm thấy lượt khám")
        return reception

    # ── Queries ───────────────────────────────────────────────────────────────

    async def get_queue(
        self,
        db: AsyncSession,
        *,
        clinic_room: Optional[str],
        visit_date: date,
        q: Optional[str] = None,
    ) -> List[Reception]:
        """
        Lấy danh sách bệnh nhân đang CHECKED_IN trong ngày.

        Nếu ``clinic_room`` là ``None`` → trả về tất cả phòng (dành cho admin).
        Thêm tham số ``q`` để tìm kiếm trong các trường bệnh nhân (tên, mã BN, CCCD, phone,...).
        """
        query = (
            select(Reception)
            .options(selectinload(Reception.patient))
            .where(
                Reception.visit_date == visit_date,
                Reception.status == ReceptionStatus.CHECKED_IN,
            )
        )
        if clinic_room:
            query = query.where(Reception.clinic_room == clinic_room)

        # Search across patient fields when q provided
        if q and q.strip():
            kw = f"%{q.strip()}%"
            query = (
                query.join(Patient)
                .where(
                    or_(
                        Patient.full_name.ilike(kw),
                        Patient.patient_code.ilike(kw),
                        Patient.cccd.ilike(kw),
                        Patient.phone.ilike(kw),
                        Patient.address.ilike(kw),
                    )
                )
            )

        query = query.order_by(
            Reception.priority.desc(),
            Reception.visit_number.asc(),
            Reception.id.asc(),
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_queue_stats(
        self,
        db: AsyncSession,
        *,
        clinic_room: Optional[str],
        visit_date: date,
    ) -> QueueStatsResponse:
        """
        Thống kê nhanh số BN theo từng ``visit_status`` trong ngày.

        Nếu ``clinic_room`` là ``None`` → thống kê tất cả phòng.
        """
        base_active = [
            Reception.visit_date == visit_date,
            Reception.status == ReceptionStatus.CHECKED_IN,
        ]
        base_done = [
            Reception.visit_date == visit_date,
            Reception.status == ReceptionStatus.COMPLETED,
        ]
        if clinic_room:
            base_active.append(Reception.clinic_room == clinic_room)
            base_done.append(Reception.clinic_room == clinic_room)

        active_result = await db.execute(
            select(Reception.visit_status, func.count(Reception.id))
            .where(and_(*base_active))
            .group_by(Reception.visit_status)
        )
        counts = {r[0]: r[1] for r in active_result.all()}

        done_result = await db.execute(
            select(func.count(Reception.id)).where(and_(*base_done))
        )
        done_count = done_result.scalar_one() or 0
        active_total = sum(counts.values())

        return QueueStatsResponse(
            clinic_room=clinic_room or "Tất cả",
            visit_date=visit_date,
            total=active_total + done_count,
            waiting=counts.get(VisitStatus.WAITING, 0),
            cls=counts.get(VisitStatus.CLS, 0),
            cls_result=counts.get(VisitStatus.CLS_RESULT, 0),
            revisit=counts.get(VisitStatus.REVISIT, 0),
            done=done_count,
        )

    # ── Mutations ─────────────────────────────────────────────────────────────

    async def update_visit_status(
        self,
        db: AsyncSession,
        *,
        reception_id: int,
        body: VisitStatusUpdate,
        updated_by: str,
    ) -> Reception:
        """
        Cập nhật trạng thái xử lý bệnh nhân tại phòng khám.

        Broadcast real-time tới quầy tiếp đón sau khi thay đổi.

        Args:
            db: Async database session.
            reception_id: ID lượt tiếp đón cần cập nhật.
            body: :class:`~app.schemas.doctor.VisitStatusUpdate`.
            updated_by: Username của bác sĩ thực hiện (audit).

        Returns:
            :class:`~app.models.reception.Reception` đã cập nhật.

        Raises:
            HTTPException 404: Không tìm thấy lượt tiếp đón.
        """
        reception = await self._get_reception_or_404(db, reception_id)

        reception.visit_status = body.visit_status
        reception.updated_by = updated_by
        db.add(reception)
        await db.flush()
        await db.refresh(reception)

        logger.info(
            "visit_status updated | reception_id=%s visit_status=%s updated_by=%s",
            reception_id, body.visit_status.value, updated_by,
        )

        await ws_manager.broadcast("reception", {
            "type": "doctor_queue_update",
            "data": {
                "reception_id": reception_id,
                "visit_status": body.visit_status.value,
                "clinic_room": reception.clinic_room,
            },
        })
        return reception

    async def complete_visit(
        self,
        db: AsyncSession,
        *,
        reception_id: int,
        updated_by: str,
    ) -> Reception:
        """
        Bác sĩ kết thúc lượt khám — Reception → COMPLETED, VisitStatus → DONE.

        Idempotent: nếu đã COMPLETED thì trả về nguyên kết quả hiện có.

        Args:
            db: Async database session.
            reception_id: ID lượt tiếp đón cần kết thúc.
            updated_by: Username của bác sĩ thực hiện (audit).

        Returns:
            :class:`~app.models.reception.Reception` với status COMPLETED.

        Raises:
            HTTPException 404: Không tìm thấy lượt tiếp đón.
        """
        reception = await self._get_reception_or_404(db, reception_id)

        # Idempotent guard
        if reception.status == ReceptionStatus.COMPLETED:
            return reception

        reception.status = ReceptionStatus.COMPLETED
        reception.visit_status = VisitStatus.DONE
        reception.completed_at = datetime.now(timezone.utc)
        reception.updated_by = updated_by
        db.add(reception)
        await db.flush()
        await db.refresh(reception)

        logger.info(
            "visit completed | reception_id=%s updated_by=%s",
            reception_id, updated_by,
        )

        await ws_manager.broadcast("reception", {
            "type": "doctor_queue_update",
            "data": {
                "reception_id": reception_id,
                "visit_status": VisitStatus.DONE.value,
                "clinic_room": reception.clinic_room,
            },
        })
        return reception

    async def transfer_patient(
        self,
        db: AsyncSession,
        *,
        reception_id: int,
        body: TransferRequest,
        updated_by: str,
    ) -> Reception:
        """
        Chuyển bệnh nhân sang phòng khám khác trong cùng cơ sở.

        Business rules:
        - Cập nhật ``clinic_room`` và reset ``visit_status`` về WAITING.
        - Lý do chuyển phòng được append vào ``internal_note``.
        - Broadcast tới cả phòng cũ và phòng mới.

        Args:
            db: Async database session.
            reception_id: ID lượt tiếp đón cần chuyển phòng.
            body: :class:`~app.schemas.doctor.TransferRequest`.
            updated_by: Username của bác sĩ thực hiện (audit).

        Returns:
            :class:`~app.models.reception.Reception` đã cập nhật với phòng mới.

        Raises:
            HTTPException 404: Không tìm thấy lượt tiếp đón.
        """
        reception = await self._get_reception_or_404(db, reception_id)

        old_room = reception.clinic_room
        reception.clinic_room = body.clinic_room
        reception.visit_status = VisitStatus.WAITING  # Reset về chờ khám ở phòng mới
        reception.updated_by = updated_by

        if body.note:
            existing_note = reception.internal_note or ""
            reception.internal_note = (
                f"{existing_note}\n"
                f"[Chuyển từ {old_room} → {body.clinic_room}]: {body.note}"
            ).strip()

        db.add(reception)
        await db.flush()
        await db.refresh(reception)

        logger.info(
            "patient transferred | reception_id=%s from=%s to=%s updated_by=%s",
            reception_id, old_room, body.clinic_room, updated_by,
        )

        # Thông báo cả hai phòng
        for room in {old_room, body.clinic_room} - {None}:
            await ws_manager.broadcast("reception", {
                "type": "doctor_queue_update",
                "data": {"reception_id": reception_id, "clinic_room": room},
            })

        return reception


# Singleton dùng toàn ứng dụng
doctor_service = DoctorService()
"""Singleton instance của :class:`DoctorService`."""
