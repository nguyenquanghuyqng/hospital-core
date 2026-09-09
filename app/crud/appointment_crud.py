"""
CRUD cho lịch hẹn khám.
"""
from datetime import date, datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate


def _gen_appt_no(appt_id: int) -> str:
    from datetime import date as d
    return f"HA{d.today().year}{appt_id:06d}"


class CRUDAppointment(CRUDBase[Appointment]):

    async def get_full(self, db: AsyncSession, appt_id: int) -> Optional[Appointment]:
        row = await db.execute(
            select(Appointment)
            .options(
                selectinload(Appointment.patient),
                selectinload(Appointment.doctor),
            )
            .where(Appointment.id == appt_id)
        )
        return row.scalar_one_or_none()

    async def list_by_date(
        self,
        db: AsyncSession,
        *,
        scheduled_date: date,
        doctor_id: Optional[int] = None,
        department: Optional[str] = None,
        status: Optional[AppointmentStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Appointment], int]:
        """Danh sách lịch hẹn theo ngày."""
        conditions = [Appointment.scheduled_date == scheduled_date]
        if doctor_id:
            conditions.append(Appointment.doctor_id == doctor_id)
        if department:
            conditions.append(Appointment.department == department)
        if status:
            conditions.append(Appointment.status == status)

        query = select(Appointment).where(and_(*conditions))
        total = (await db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar_one()
        items = list((await db.execute(
            query.order_by(
                Appointment.scheduled_time.nullslast(),
                Appointment.id,
            ).offset(skip).limit(limit)
        )).scalars().all())
        return items, total

    async def list_by_patient(
        self,
        db: AsyncSession,
        patient_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Appointment], int]:
        query = select(Appointment).where(Appointment.patient_id == patient_id)
        total = (await db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar_one()
        items = list((await db.execute(
            query.order_by(Appointment.scheduled_date.desc())
            .offset(skip).limit(limit)
        )).scalars().all())
        return items, total

    async def create_appointment(
        self,
        db: AsyncSession,
        *,
        obj_in: AppointmentCreate,
        created_by: Optional[str] = None,
    ) -> Appointment:
        data = obj_in.model_dump()
        data["appointment_no"] = "DRAFT"
        data["created_by"] = created_by
        appt = Appointment(**data)
        db.add(appt)
        await db.flush()
        appt.appointment_no = _gen_appt_no(appt.id)
        db.add(appt)
        await db.flush()
        await db.refresh(appt)
        return appt

    async def update_appointment(
        self,
        db: AsyncSession,
        *,
        db_obj: Appointment,
        obj_in: AppointmentUpdate,
    ) -> Appointment:
        data = obj_in.model_dump(exclude_unset=True)
        now = datetime.now(timezone.utc)

        # Ghi timestamp theo trạng thái
        if "status" in data:
            new_status = data["status"]
            if new_status == AppointmentStatus.CONFIRMED and not db_obj.confirmed_at:
                data["confirmed_at"] = now
            elif new_status == AppointmentStatus.ARRIVED and not db_obj.arrived_at:
                data["arrived_at"] = now
            elif new_status == AppointmentStatus.COMPLETED and not db_obj.completed_at:
                data["completed_at"] = now
            elif new_status == AppointmentStatus.CANCELLED and not db_obj.cancelled_at:
                data["cancelled_at"] = now

        for k, v in data.items():
            setattr(db_obj, k, v)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_today_count(
        self, db: AsyncSession, *, doctor_id: Optional[int] = None
    ) -> int:
        """Số lịch hẹn hôm nay."""
        today = date.today()
        conditions = [Appointment.scheduled_date == today]
        if doctor_id:
            conditions.append(Appointment.doctor_id == doctor_id)
        result = await db.execute(
            select(func.count()).where(and_(*conditions))
        )
        return result.scalar_one()


crud_appointment = CRUDAppointment(Appointment)
