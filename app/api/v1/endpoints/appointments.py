"""
Appointment endpoints — quản lý lịch hẹn khám.

Routes:
  POST  /appointments                     — Tạo lịch hẹn mới
  GET   /appointments                     — Danh sách theo ngày / bác sĩ
  GET   /appointments/{id}               — Chi tiết lịch hẹn
  PUT   /appointments/{id}               — Cập nhật lịch hẹn
  POST  /appointments/{id}/confirm       — Xác nhận lịch hẹn
  POST  /appointments/{id}/arrive        — Ghi nhận bệnh nhân đến
  POST  /appointments/{id}/complete      — Hoàn tất
  POST  /appointments/{id}/cancel        — Huỷ lịch hẹn
  GET   /appointments/patient/{id}       — Lịch hẹn của bệnh nhân
"""
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import require_receptionist, require_clinical, get_current_user
from app.models.user import User
from app.models.enums import AppointmentStatus
from app.crud.appointment_crud import crud_appointment
from app.crud.catalog import crud_audit
from app.schemas.appointment import (
    AppointmentCreate, AppointmentUpdate,
    AppointmentResponse, AppointmentList,
)

router = APIRouter(prefix="/appointments", tags=["Appointments - Lịch hẹn"])


async def _get_or_404(db: AsyncSession, appt_id: int):
    appt = await crud_appointment.get_full(db, appt_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch hẹn")
    return appt


# ── Tạo mới ────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo lịch hẹn mới",
)
async def create_appointment(
    obj_in: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_receptionist),
):
    """
    Lễ tân hoặc bác sĩ (admin) tạo lịch hẹn mới / hẹn tái khám.
    ``appointment_type``: ``new`` | ``revisit`` | ``followup``.
    """
    if obj_in.scheduled_date < date.today():
        raise HTTPException(status_code=400, detail="Ngày hẹn phải là hôm nay hoặc tương lai")

    appt = await crud_appointment.create_appointment(
        db, obj_in=obj_in,
        created_by=current_user.username,
    )
    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="CREATE",
        table_name="appointments",
        record_id=appt.id,
        new_data={
            "appointment_no": appt.appointment_no,
            "patient_id": appt.patient_id,
            "scheduled_date": str(appt.scheduled_date),
        },
        description=f"Tạo lịch hẹn {appt.appointment_no}",
    )
    await db.commit()
    await db.refresh(appt)
    return appt


# ── Tra cứu ────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=List[AppointmentList],
    summary="Danh sách lịch hẹn theo ngày",
)
async def list_appointments(
    scheduled_date: date = Query(default_factory=date.today, description="Ngày lọc"),
    doctor_id: Optional[int] = Query(None),
    department: Optional[str] = Query(None),
    appt_status: Optional[AppointmentStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_receptionist),
):
    items, _ = await crud_appointment.list_by_date(
        db,
        scheduled_date=scheduled_date,
        doctor_id=doctor_id,
        department=department,
        status=appt_status,
        skip=skip,
        limit=limit,
    )
    return items


@router.get(
    "/patient/{patient_id}",
    response_model=List[AppointmentList],
    summary="Lịch hẹn của bệnh nhân",
)
async def list_by_patient(
    patient_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_receptionist),
):
    items, _ = await crud_appointment.list_by_patient(db, patient_id, skip=skip, limit=limit)
    return items


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Chi tiết lịch hẹn",
)
async def get_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_receptionist),
):
    return await _get_or_404(db, appointment_id)


# ── Cập nhật ───────────────────────────────────────────────────────────────────

@router.put(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Cập nhật lịch hẹn",
)
async def update_appointment(
    appointment_id: int,
    obj_in: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_receptionist),
):
    appt = await _get_or_404(db, appointment_id)
    if appt.status in (AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED):
        raise HTTPException(status_code=400,
                            detail="Không thể chỉnh sửa lịch hẹn đã hoàn tất hoặc đã huỷ")
    updated = await crud_appointment.update_appointment(db, db_obj=appt, obj_in=obj_in)
    await db.commit()
    return updated


# ── Workflow transitions ────────────────────────────────────────────────────────

@router.post("/{appointment_id}/confirm", response_model=AppointmentResponse, summary="Xác nhận lịch hẹn")
async def confirm_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_receptionist),
):
    appt = await _get_or_404(db, appointment_id)
    if appt.status != AppointmentStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail="Chỉ xác nhận được lịch ở trạng thái SCHEDULED")
    updated = await crud_appointment.update_appointment(
        db, db_obj=appt,
        obj_in=AppointmentUpdate(status=AppointmentStatus.CONFIRMED),
    )
    await db.commit()
    return updated


@router.post("/{appointment_id}/arrive", response_model=AppointmentResponse, summary="Bệnh nhân đã đến")
async def arrive_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_receptionist),
):
    appt = await _get_or_404(db, appointment_id)
    if appt.status not in (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED):
        raise HTTPException(status_code=400, detail="Lịch hẹn không ở trạng thái phù hợp")
    updated = await crud_appointment.update_appointment(
        db, db_obj=appt,
        obj_in=AppointmentUpdate(status=AppointmentStatus.ARRIVED),
    )
    await db.commit()
    return updated


@router.post("/{appointment_id}/complete", response_model=AppointmentResponse, summary="Hoàn tất lịch hẹn")
async def complete_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_clinical),
):
    appt = await _get_or_404(db, appointment_id)
    if appt.status not in (AppointmentStatus.ARRIVED, AppointmentStatus.CONFIRMED):
        raise HTTPException(status_code=400, detail="Lịch hẹn chưa đến hoặc chưa xác nhận")
    updated = await crud_appointment.update_appointment(
        db, db_obj=appt,
        obj_in=AppointmentUpdate(status=AppointmentStatus.COMPLETED),
    )
    await db.commit()
    return updated


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse, summary="Huỷ lịch hẹn")
async def cancel_appointment(
    appointment_id: int,
    obj_in: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_receptionist),
):
    """Truyền ``cancel_reason`` trong body để ghi lý do huỷ."""
    appt = await _get_or_404(db, appointment_id)
    if appt.status in (AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Lịch hẹn đã ở trạng thái cuối")
    updated = await crud_appointment.update_appointment(
        db, db_obj=appt,
        obj_in=AppointmentUpdate(
            status=AppointmentStatus.CANCELLED,
            cancel_reason=obj_in.cancel_reason,
        ),
    )
    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="UPDATE",
        table_name="appointments",
        record_id=appointment_id,
        new_data={"status": "cancelled", "cancel_reason": obj_in.cancel_reason},
        description=f"Huỷ lịch hẹn {appt.appointment_no}",
    )
    await db.commit()
    return updated
