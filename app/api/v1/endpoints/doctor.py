"""
Doctor endpoints — giao diện dành riêng cho bác sĩ tại phòng khám.

Routes:
  GET   /doctor/queue                         — danh sách BN chờ khám theo phòng
  GET   /doctor/queue/stats                   — đếm nhanh chờ / đã khám
  PATCH /doctor/receptions/{id}/visit-status  — cập nhật trạng thái xử lý
  POST  /doctor/receptions/{id}/done          — kết thúc khám (→ COMPLETED)
  PATCH /doctor/receptions/{id}/transfer      — chuyển khám sang phòng khác
"""
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.core.deps import get_current_user, require_doctor
from app.models.user import User
from app.models.reception import Reception
from app.models.patient import Patient
from app.models.enums import ReceptionStatus, VisitStatus
from app.schemas.reception import ReceptionResponse
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/doctor", tags=["Doctor - Phòng khám bác sĩ"])


# ── Schemas ───────────────────────────────────────────────────────────────────
class VisitStatusUpdate(BaseModel):
    visit_status: VisitStatus


class TransferRequest(BaseModel):
    clinic_room: str
    note: Optional[str] = None


class QueueStatsResponse(BaseModel):
    clinic_room:  str
    visit_date:   date
    total:        int
    waiting:      int
    cls:          int
    cls_result:   int
    revisit:      int
    done:         int


class PatientSummary(BaseModel):
    """Thông tin hành chính rút gọn hiển thị khi chọn BN."""
    id:           int
    patient_code: Optional[str]
    full_name:    str
    date_of_birth: Optional[date]
    birth_year:   Optional[int]
    gender:       Optional[str]
    ethnicity_name:  Optional[str]
    nationality_name: Optional[str]
    occupation:   Optional[str]
    address_street:  Optional[str]
    address_village: Optional[str]
    address_ward_name:     Optional[str]
    address_district_name: Optional[str]
    address_province_name: Optional[str]
    phone: Optional[str]

    model_config = {"from_attributes": True}


class QueueItem(BaseModel):
    """Một dòng trong danh sách chờ khám."""
    id:            int          # reception id
    visit_number:  Optional[int]
    visit_time:    Optional[str]
    visit_status:  VisitStatus
    status:        ReceptionStatus
    patient:       PatientSummary
    patient_type:  Optional[str]  # Mới / Cũ
    subject_name:  Optional[str]  # BHYT / DV
    priority:      int

    model_config = {"from_attributes": True}


# ── Helper ────────────────────────────────────────────────────────────────────
def _resolve_clinic_room(
    clinic_room_param: Optional[str],
    current_user: User,
) -> str:
    """Ưu tiên param truyền vào, fallback về phòng của user đăng nhập."""
    room = clinic_room_param or current_user.clinic_room
    if not room:
        raise HTTPException(
            status_code=400,
            detail="Chưa xác định phòng khám. Vui lòng chọn phòng hoặc cập nhật hồ sơ bác sĩ.",
        )
    return room


# ── Danh sách chờ khám ────────────────────────────────────────────────────────
@router.get(
    "/queue",
    response_model=list[QueueItem],
    summary="Danh sách bệnh nhân chờ khám",
)
async def get_doctor_queue(
    clinic_room: Optional[str] = Query(None, description="Phòng khám; mặc định phòng của bác sĩ đăng nhập"),
    visit_date:  Optional[date] = Query(None, description="Ngày khám, mặc định hôm nay"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Trả về danh sách BN đang chờ khám (CHECKED_IN) tại phòng,
    sắp xếp: ưu tiên cao → số khám tăng dần.
    """
    room = _resolve_clinic_room(clinic_room, current_user)
    target_date = visit_date or date.today()

    result = await db.execute(
        select(Reception)
        .options(selectinload(Reception.patient))
        .where(
            and_(
                Reception.visit_date == target_date,
                Reception.clinic_room == room,
                Reception.status == ReceptionStatus.CHECKED_IN,
            )
        )
        .order_by(Reception.priority.desc(), Reception.visit_number.asc(), Reception.id.asc())
    )
    receptions = list(result.scalars().all())
    return receptions


# ── Thống kê nhanh ────────────────────────────────────────────────────────────
@router.get(
    "/queue/stats",
    response_model=QueueStatsResponse,
    summary="Thống kê nhanh: chờ / đã khám theo phòng",
)
async def get_queue_stats(
    clinic_room: Optional[str] = Query(None),
    visit_date:  Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    room = _resolve_clinic_room(clinic_room, current_user)
    target_date = visit_date or date.today()

    # Count active (CHECKED_IN) patients by visit_status
    active_result = await db.execute(
        select(Reception.visit_status, func.count(Reception.id))
        .where(
            and_(
                Reception.visit_date == target_date,
                Reception.clinic_room == room,
                Reception.status == ReceptionStatus.CHECKED_IN,
            )
        )
        .group_by(Reception.visit_status)
    )
    counts = {r[0]: r[1] for r in active_result.all()}

    # Count completed patients today (they have COMPLETED status + DONE visit_status)
    done_result = await db.execute(
        select(func.count(Reception.id))
        .where(
            and_(
                Reception.visit_date == target_date,
                Reception.clinic_room == room,
                Reception.status == ReceptionStatus.COMPLETED,
            )
        )
    )
    done_count = done_result.scalar_one() or 0

    active_total = sum(counts.values())
    return QueueStatsResponse(
        clinic_room=room,
        visit_date=target_date,
        total=active_total + done_count,
        waiting=counts.get(VisitStatus.WAITING, 0),
        cls=counts.get(VisitStatus.CLS, 0),
        cls_result=counts.get(VisitStatus.CLS_RESULT, 0),
        revisit=counts.get(VisitStatus.REVISIT, 0),
        done=done_count,
    )


# ── Cập nhật trạng thái xử lý ─────────────────────────────────────────────────
@router.patch(
    "/receptions/{reception_id}/visit-status",
    response_model=QueueItem,
    summary="Cập nhật trạng thái xử lý bệnh nhân",
)
async def update_visit_status(
    reception_id: int,
    body: VisitStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Bác sĩ cập nhật trạng thái: Chờ khám → CLS → Có KQ → Tái khám → Xong.
    """
    result = await db.execute(
        select(Reception)
        .options(selectinload(Reception.patient))
        .where(Reception.id == reception_id)
    )
    reception = result.scalar_one_or_none()
    if not reception:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt khám")

    reception.visit_status = body.visit_status
    db.add(reception)
    await db.flush()
    await db.refresh(reception)

    # Broadcast cập nhật real-time cho room doctor
    await ws_manager.broadcast("reception", {
        "type": "doctor_queue_update",
        "data": {
            "reception_id": reception_id,
            "visit_status": body.visit_status.value,
            "clinic_room":  reception.clinic_room,
        },
    })

    return reception


# ── Kết thúc khám ────────────────────────────────────────────────────────────
@router.post(
    "/receptions/{reception_id}/done",
    response_model=QueueItem,
    summary="Kết thúc khám → COMPLETED",
)
async def complete_visit(
    reception_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    result = await db.execute(
        select(Reception)
        .options(selectinload(Reception.patient))
        .where(Reception.id == reception_id)
    )
    reception = result.scalar_one_or_none()
    if not reception:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt khám")
    if reception.status == ReceptionStatus.COMPLETED:
        return reception  # idempotent

    reception.status       = ReceptionStatus.COMPLETED
    reception.visit_status = VisitStatus.DONE
    reception.completed_at = datetime.now(timezone.utc)
    db.add(reception)
    await db.flush()
    await db.refresh(reception)

    await ws_manager.broadcast("reception", {
        "type": "doctor_queue_update",
        "data": {
            "reception_id": reception_id,
            "visit_status": VisitStatus.DONE.value,
            "clinic_room":  reception.clinic_room,
        },
    })

    return reception


# ── Chuyển khám ───────────────────────────────────────────────────────────────
@router.patch(
    "/receptions/{reception_id}/transfer",
    response_model=QueueItem,
    summary="Chuyển bệnh nhân sang phòng khám khác",
)
async def transfer_patient(
    reception_id: int,
    body: TransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    result = await db.execute(
        select(Reception)
        .options(selectinload(Reception.patient))
        .where(Reception.id == reception_id)
    )
    reception = result.scalar_one_or_none()
    if not reception:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt khám")

    old_room = reception.clinic_room
    reception.clinic_room  = body.clinic_room
    reception.visit_status = VisitStatus.WAITING  # reset về chờ khám ở phòng mới

    if body.note:
        existing_note = reception.internal_note or ""
        reception.internal_note = f"{existing_note}\n[Chuyển từ {old_room} → {body.clinic_room}]: {body.note}".strip()

    db.add(reception)
    await db.flush()
    await db.refresh(reception)

    # Thông báo cả 2 phòng
    for room in {old_room, body.clinic_room} - {None}:
        await ws_manager.broadcast("reception", {
            "type": "doctor_queue_update",
            "data": {"reception_id": reception_id, "clinic_room": room},
        })

    return reception
