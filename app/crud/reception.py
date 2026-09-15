"""
CRUD operations cho model :class:`~app.models.reception.Reception`.

Quản lý toàn bộ vòng đời lượt tiếp đón: đăng ký, check-in,
hoàn tất, huỷ, và các truy vấn thống kê theo ngày / phòng khám.
"""
from datetime import date, datetime, timezone
from typing import List, Optional
from sqlalchemy import select, and_, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.reception import Reception, ReceptionStatus
from app.models.patient import Patient
from app.schemas.reception import ReceptionCreate, ReceptionUpdate, ReceptionCheckIn


class CRUDReception(CRUDBase[Reception]):
    """
    CRUD class cho Reception — kế thừa :class:`~app.crud.base.CRUDBase`.

    Bổ sung: tạo lượt tiếp đón với số khám tự tăng theo phòng/ngày,
    truy vấn có eager-load bệnh nhân, workflow transitions
    (check-in / complete / cancel), và thống kê theo ngày / phòng khám.
    """

    # ── Tạo mới ─────────────────────────────────────────────────────────────

    async def create_reception(
        self,
        db: AsyncSession,
        *,
        obj_in: ReceptionCreate,
        patient_id: int,
    ) -> Reception:
        """
        Tạo lượt tiếp đón mới với tự động điền thời gian và số khám.

        Thực hiện ba bước tự động:
        1. Đặt ``visit_date`` = hôm nay.
        2. Điền ``visit_time`` = giờ hiện tại nếu không được truyền vào.
        3. Sinh ``visit_number`` tự tăng theo phòng khám trong ngày.

        Args:
            db: Async database session.
            obj_in: Schema :class:`~app.schemas.reception.ReceptionCreate`.
            patient_id: ID của bệnh nhân đã tồn tại trong database.

        Returns:
            :class:`~app.models.reception.Reception` vừa tạo với
            ``status=CHECKED_IN`` để bệnh nhân xuất hiện ngay trong danh sách chờ khám.
        """
        data = obj_in.model_dump(exclude={"patient_id", "patient_data"})
        data["patient_id"] = patient_id
        data["visit_date"] = date.today()
        data["status"] = ReceptionStatus.CHECKED_IN
        data["checked_in_at"] = datetime.now(timezone.utc)

        # Tự điền phòng khám nếu không có để đảm bảo luôn có số khám
        clinic_room = (data.get("clinic_room") or "").strip()
        if not clinic_room:
            clinic_room = "Phòng khám"
        data["clinic_room"] = clinic_room

        # Tự điền giờ đăng ký nếu không có
        if not data.get("visit_time"):
            data["visit_time"] = datetime.now().strftime("%H:%M")

        # Tự sinh visit_number theo phòng khám trong ngày
        if data.get("visit_number") is None:
            data["visit_number"] = await self._next_visit_number(
                db,
                visit_date=data["visit_date"],
                clinic_room=data["clinic_room"],
            )

        return await self.create(db, obj_in=data)

    async def _next_visit_number(
        self,
        db: AsyncSession,
        *,
        visit_date: date,
        clinic_room: str,
    ) -> int:
        """
        Lấy số khám tiếp theo của một phòng trong ngày.

        Truy vấn ``MAX(visit_number)`` theo (visit_date, clinic_room)
        rồi cộng thêm 1.

        Args:
            db: Async database session.
            visit_date: Ngày khám cần tính.
            clinic_room: Tên phòng khám cần tính.

        Returns:
            Số nguyên là số khám kế tiếp (bắt đầu từ 1 nếu phòng chưa có lượt nào).
        """
        result = await db.execute(
            select(func.coalesce(func.max(Reception.visit_number), 0))
            .where(
                and_(
                    Reception.visit_date == visit_date,
                    Reception.clinic_room == clinic_room,
                )
            )
        )
        return (result.scalar_one() or 0) + 1

    # ── Truy vấn ─────────────────────────────────────────────────────────────

    async def get_with_patient(
        self, db: AsyncSession, reception_id: int
    ) -> Optional[Reception]:
        """
        Lấy chi tiết lượt tiếp đón kèm eager-load thông tin bệnh nhân.

        Args:
            db: Async database session.
            reception_id: ID lượt tiếp đón.

        Returns:
            :class:`~app.models.reception.Reception` với ``patient`` đã load,
            hoặc ``None`` nếu không tìm thấy.
        """
        result = await db.execute(
            select(Reception)
            .options(selectinload(Reception.patient))
            .where(Reception.id == reception_id)
        )
        return result.scalar_one_or_none()

    async def get_by_date(
        self,
        db: AsyncSession,
        *,
        visit_date: date,
        status: Optional[ReceptionStatus] = None,
        clinic_room: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Reception]:
        """
        Danh sách lượt tiếp đón theo ngày với eager-load bệnh nhân.

        Kết quả được sắp xếp ưu tiên cao trước, sau đó theo ``visit_number``
        tăng dần để phản ánh đúng thứ tự khám.

        Args:
            db: Async database session.
            visit_date: Ngày khám cần truy vấn.
            status: Lọc theo trạng thái tiếp đón (tuỳ chọn).
            clinic_room: Lọc theo phòng khám (tuỳ chọn).
            skip: Offset phân trang.
            limit: Số bản ghi tối đa.

        Returns:
            Danh sách :class:`~app.models.reception.Reception` với ``patient`` đã load.
        """
        query = (
            select(Reception)
            .options(selectinload(Reception.patient))
            .where(Reception.visit_date == visit_date)
        )
        if status:
            query = query.where(Reception.status == status)
        if clinic_room:
            query = query.where(Reception.clinic_room == clinic_room)
        query = (
            query
            .order_by(Reception.priority.desc(), Reception.visit_number.asc(), Reception.id.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_by_date(
        self,
        db: AsyncSession,
        *,
        visit_date: date,
        status: Optional[ReceptionStatus] = None,
        clinic_room: Optional[str] = None,
    ) -> int:
        """
        Đếm số lượt tiếp đón theo ngày, tuỳ chọn lọc theo trạng thái và phòng.

        Dùng kết hợp với :meth:`get_by_date` để tính ``total_pages`` phân trang.

        Args:
            db: Async database session.
            visit_date: Ngày khám cần đếm.
            status: Lọc theo trạng thái (tuỳ chọn).
            clinic_room: Lọc theo phòng khám (tuỳ chọn).

        Returns:
            Tổng số bản ghi phù hợp.
        """
        query = select(func.count()).select_from(Reception).where(
            Reception.visit_date == visit_date
        )
        if status:
            query = query.where(Reception.status == status)
        if clinic_room:
            query = query.where(Reception.clinic_room == clinic_room)
        result = await db.execute(query)
        return result.scalar_one()

    async def get_by_patient(
        self,
        db: AsyncSession,
        patient_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Reception]:
        """
        Lịch sử khám của một bệnh nhân, sắp xếp mới nhất trước.

        Args:
            db: Async database session.
            patient_id: ID bệnh nhân cần tra lịch sử.
            skip: Offset phân trang.
            limit: Số bản ghi tối đa.

        Returns:
            Danh sách :class:`~app.models.reception.Reception` của bệnh nhân.
        """
        result = await db.execute(
            select(Reception)
            .where(Reception.patient_id == patient_id)
            .order_by(Reception.visit_date.desc(), Reception.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_queue_ticket(
        self, db: AsyncSession, queue_ticket_id: int
    ) -> Optional[Reception]:
        """
        Lấy lượt tiếp đón theo ID số thứ tự (1-1 relationship).

        Args:
            db: Async database session.
            queue_ticket_id: ID của :class:`~app.models.queue_ticket.QueueTicket`.

        Returns:
            :class:`~app.models.reception.Reception` kèm ``patient`` đã load,
            hoặc ``None`` nếu chưa có lượt tiếp đón nào gắn với số thứ tự này.
        """
        result = await db.execute(
            select(Reception)
            .options(selectinload(Reception.patient))
            .where(Reception.queue_ticket_id == queue_ticket_id)
        )
        return result.scalar_one_or_none()

    # ── Workflow transitions ──────────────────────────────────────────────────

    async def check_in(
        self,
        db: AsyncSession,
        *,
        reception: Reception,
        obj_in: ReceptionCheckIn,
    ) -> Reception:
        """
        Chuyển lượt tiếp đón từ PENDING → CHECKED_IN.

        Nếu lượt tiếp đón đã ở trạng thái CHECKED_IN thì coi như thao tác idempotent
        và chỉ cập nhật các trường tùy chọn (số thứ tự, nhân viên tiếp đón, ghi chú).

        Args:
            db: Async database session.
            reception: Instance :class:`~app.models.reception.Reception` đang ở PENDING hoặc CHECKED_IN.
            obj_in: Schema :class:`~app.schemas.reception.ReceptionCheckIn`.

        Returns:
            :class:`~app.models.reception.Reception` đã cập nhật sang CHECKED_IN.
        """
        if reception.status == ReceptionStatus.CHECKED_IN:
            if reception.checked_in_at is None:
                reception.checked_in_at = datetime.now(timezone.utc)
        else:
            reception.status = ReceptionStatus.CHECKED_IN
            reception.checked_in_at = datetime.now(timezone.utc)

        if obj_in.queue_ticket_id is not None:
            reception.queue_ticket_id = obj_in.queue_ticket_id
        if obj_in.receptionist_name is not None:
            reception.receptionist_name = obj_in.receptionist_name
        if obj_in.internal_note is not None:
            reception.internal_note = obj_in.internal_note

        db.add(reception)
        await db.flush()
        await db.refresh(reception)
        return reception

    async def complete_reception(
        self, db: AsyncSession, *, reception: Reception
    ) -> Reception:
        """
        Chuyển lượt tiếp đón sang trạng thái COMPLETED và VisitStatus → DONE.

        Ghi ``completed_at`` = thời điểm hiện tại.
        Đặt ``visit_status = DONE`` để đồng bộ trạng thái xử lý tại phòng khám.

        Args:
            db: Async database session.
            reception: Instance :class:`~app.models.reception.Reception` cần hoàn tất.

        Returns:
            :class:`~app.models.reception.Reception` đã cập nhật sang COMPLETED.
        """
        from app.models.enums import VisitStatus  # local import tránh circular
        reception.status       = ReceptionStatus.COMPLETED
        reception.visit_status = VisitStatus.DONE
        reception.completed_at = datetime.now(timezone.utc)
        db.add(reception)
        await db.flush()
        await db.refresh(reception)
        return reception

    async def cancel_reception(
        self, db: AsyncSession, *, reception: Reception
    ) -> Reception:
        """
        Huỷ lượt tiếp đón (→ CANCELLED).

        Args:
            db: Async database session.
            reception: Instance :class:`~app.models.reception.Reception` cần huỷ.

        Returns:
            :class:`~app.models.reception.Reception` đã cập nhật sang CANCELLED.
        """
        reception.status = ReceptionStatus.CANCELLED
        db.add(reception)
        await db.flush()
        await db.refresh(reception)
        return reception

    async def update_reception(
        self,
        db: AsyncSession,
        *,
        db_obj: Reception,
        obj_in: ReceptionUpdate,
    ) -> Reception:
        """
        Cập nhật thông tin lượt tiếp đón (wrapper của :meth:`~CRUDBase.update`).

        Args:
            db: Async database session.
            db_obj: Instance :class:`~app.models.reception.Reception` hiện có.
            obj_in: Schema :class:`~app.schemas.reception.ReceptionUpdate`.

        Returns:
            :class:`~app.models.reception.Reception` đã cập nhật.
        """
        return await self.update(db, db_obj=db_obj, obj_in=obj_in)

    # ── Thống kê ─────────────────────────────────────────────────────────────

    async def get_today_stats(self, db: AsyncSession) -> dict:
        """
        Thống kê tổng hợp số lượt tiếp đón hôm nay theo từng trạng thái.

        Dùng cho dashboard và broadcast WebSocket khi có thay đổi.

        Args:
            db: Async database session.

        Returns:
            Dict chứa: ``visit_date``, ``total``, ``pending``,
            ``checked_in``, ``completed``, ``cancelled``.
        """
        today = date.today()
        result = await db.execute(
            select(Reception.status, func.count(Reception.id))
            .where(Reception.visit_date == today)
            .group_by(Reception.status)
        )
        rows = result.all()
        counts = {r[0]: r[1] for r in rows}
        return {
            "visit_date":  today,
            "total":       sum(counts.values()),
            "pending":     counts.get(ReceptionStatus.PENDING, 0),
            "checked_in":  counts.get(ReceptionStatus.CHECKED_IN, 0),
            "completed":   counts.get(ReceptionStatus.COMPLETED, 0),
            "cancelled":   counts.get(ReceptionStatus.CANCELLED, 0),
        }

    async def get_clinic_room_stats(
        self,
        db: AsyncSession,
        *,
        visit_date: Optional[date] = None,
    ) -> dict:
        """
        Thống kê số lượt khám theo từng phòng khám trong ngày.

        Phân loại mỗi phòng theo: Tổng / Chưa tiếp nhận (PENDING) /
        BHYT (subject_type=1) / Dịch vụ (subject_type≠1).

        Args:
            db: Async database session.
            visit_date: Ngày cần thống kê (mặc định hôm nay).

        Returns:
            Dict chứa:
            - ``visit_date``: ngày thống kê.
            - ``rooms``: list dict mỗi phòng (clinic_room, total, pending, bhyt, service).
            - ``total_all``, ``total_pending``, ``total_bhyt``, ``total_service``:
              tổng cộng toàn bệnh viện.
        """
        target = visit_date or date.today()

        result = await db.execute(
            select(
                Reception.clinic_room,
                func.count(Reception.id).label("total"),
                func.sum(
                    case((Reception.status == ReceptionStatus.PENDING, 1), else_=0)
                ).label("pending"),
                func.sum(
                    case((Reception.subject_type == "1", 1), else_=0)
                ).label("bhyt"),
                func.sum(
                    case((Reception.subject_type != "1", 1), else_=0)
                ).label("service"),
            )
            .where(
                and_(
                    Reception.visit_date == target,
                    Reception.clinic_room.isnot(None),
                )
            )
            .group_by(Reception.clinic_room)
            .order_by(Reception.clinic_room)
        )
        rows = result.all()

        rooms = [
            {
                "clinic_room": r.clinic_room,
                "total":   r.total   or 0,
                "pending": r.pending or 0,
                "bhyt":    r.bhyt    or 0,
                "service": r.service or 0,
            }
            for r in rows
        ]

        return {
            "visit_date":    target,
            "rooms":         rooms,
            "total_all":     sum(r["total"]   for r in rooms),
            "total_pending": sum(r["pending"] for r in rooms),
            "total_bhyt":    sum(r["bhyt"]    for r in rooms),
            "total_service": sum(r["service"] for r in rooms),
        }


crud_reception = CRUDReception(Reception)
"""Singleton instance của :class:`CRUDReception` dùng toàn ứng dụng."""
