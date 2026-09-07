from datetime import date, datetime, timezone, time
from typing import List, Optional
from sqlalchemy import select, and_, func, case, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.reception import Reception, ReceptionStatus
from app.models.patient import Patient
from app.schemas.reception import ReceptionCreate, ReceptionUpdate, ReceptionCheckIn


class CRUDReception(CRUDBase[Reception]):

    # ── Tạo mới ─────────────────────────────────────────────────────

    async def create_reception(
        self,
        db: AsyncSession,
        *,
        obj_in: ReceptionCreate,
        patient_id: int,
    ) -> Reception:
        """
        Tạo một lần tiếp đón mới.
        - visit_date = hôm nay
        - visit_time = giờ hiện tại nếu không truyền vào
        - visit_number tự tăng theo phòng khám trong ngày
        """
        data = obj_in.model_dump(exclude={"patient_id", "patient_data"})
        data["patient_id"] = patient_id
        data["visit_date"] = date.today()
        data["status"] = ReceptionStatus.PENDING

        # Tự điền giờ đăng ký nếu không có
        if not data.get("visit_time"):
            data["visit_time"] = datetime.now().strftime("%H:%M")

        # Tự sinh visit_number theo phòng khám trong ngày
        if not data.get("visit_number") and data.get("clinic_room"):
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
        """Lấy số khám tiếp theo của phòng trong ngày."""
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

    # ── Truy vấn ────────────────────────────────────────────────────

    async def get_with_patient(
        self, db: AsyncSession, reception_id: int
    ) -> Optional[Reception]:
        """Lấy chi tiết tiếp đón kèm thông tin bệnh nhân."""
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
        """Danh sách tiếp đón theo ngày, kèm thông tin bệnh nhân."""
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
        """Lịch sử khám của một bệnh nhân."""
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
        """Lấy tiếp đón theo số thứ tự."""
        result = await db.execute(
            select(Reception)
            .options(selectinload(Reception.patient))
            .where(Reception.queue_ticket_id == queue_ticket_id)
        )
        return result.scalar_one_or_none()

    # ── Cập nhật trạng thái ──────────────────────────────────────────

    async def check_in(
        self,
        db: AsyncSession,
        *,
        reception: Reception,
        obj_in: ReceptionCheckIn,
    ) -> Reception:
        """PENDING → CHECKED_IN."""
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
        """→ COMPLETED."""
        reception.status = ReceptionStatus.COMPLETED
        reception.completed_at = datetime.now(timezone.utc)
        db.add(reception)
        await db.flush()
        await db.refresh(reception)
        return reception

    async def cancel_reception(
        self, db: AsyncSession, *, reception: Reception
    ) -> Reception:
        """→ CANCELLED."""
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
        return await self.update(db, db_obj=db_obj, obj_in=obj_in)

    # ── Thống kê ────────────────────────────────────────────────────

    async def get_today_stats(self, db: AsyncSession) -> dict:
        """Thống kê tổng hợp hôm nay theo trạng thái."""
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
        Phân loại: Tổng / Chưa tiếp nhận / BHYT / Dịch vụ.
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

        total_all     = sum(r["total"]   for r in rooms)
        total_pending = sum(r["pending"] for r in rooms)
        total_bhyt    = sum(r["bhyt"]    for r in rooms)
        total_service = sum(r["service"] for r in rooms)

        return {
            "visit_date":    target,
            "rooms":         rooms,
            "total_all":     total_all,
            "total_pending": total_pending,
            "total_bhyt":    total_bhyt,
            "total_service": total_service,
        }


crud_reception = CRUDReception(Reception)
