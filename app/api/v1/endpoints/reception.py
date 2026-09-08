"""
API endpoints quản lý tiếp đón bệnh nhân.

Routes:
  POST   /receptions/scan-cccd           — Quét CCCD → tra cứu / tạo bệnh nhân
  POST   /receptions                     — Tạo mới tiếp đón
  GET    /receptions/stats               — Thống kê hôm nay theo trạng thái
  GET    /receptions/clinic-stats        — Thống kê theo phòng khám
  GET    /receptions                     — Danh sách (phân trang, lọc)
  GET    /receptions/{id}                — Chi tiết
  PUT    /receptions/{id}                — Cập nhật
  POST   /receptions/{id}/check-in       — PENDING → CHECKED_IN
  POST   /receptions/{id}/complete       — → COMPLETED
  POST   /receptions/{id}/cancel         — → CANCELLED
"""
from datetime import date
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.crud.patient import crud_patient
from app.crud.reception import crud_reception
from app.crud.queue_ticket import crud_queue_ticket
from app.schemas.patient import PatientCreate, PatientResponse
from app.schemas.reception import (
    ReceptionCreate, ReceptionUpdate, ReceptionCheckIn,
    ReceptionResponse, ReceptionList,
    ClinicRoomStat, ClinicRoomStatResponse,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.models.reception import ReceptionStatus
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/receptions", tags=["Reception - Tiếp đón"])


# ─────────────────────────────────────────────────────────────
#  Scan CCCD
# ─────────────────────────────────────────────────────────────
class ScanCCCDRequest(PatientCreate):
    """Body khi quét CCCD: dữ liệu đọc từ chip/barcode."""
    pass


class ScanCCCDResponse(BaseModel):
    patient: PatientResponse
    is_new_patient: bool
    message: str

    model_config = {"from_attributes": True}


@router.post(
    "/scan-cccd",
    response_model=ScanCCCDResponse,
    summary="Quét CCCD — tra cứu hoặc tạo mới bệnh nhân",
)
async def scan_cccd(
    obj_in: ScanCCCDRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Nhân viên dùng thiết bị quét CCCD/CMND.
    - Đã có trong hệ thống → trả về thông tin hiện có.
    - Chưa có → tạo mới từ dữ liệu CCCD, sinh patient_code tự động.
    """
    # ScanCCCDRequest extends PatientCreate — pass directly, no need to reconstruct
    patient, is_new = await crud_patient.get_or_create_by_cccd(db, obj_in=obj_in)
    return ScanCCCDResponse(
        patient=patient,
        is_new_patient=is_new,
        message="Bệnh nhân mới — đã thêm vào hệ thống" if is_new else "Bệnh nhân đã có trong hệ thống",
    )


# ─────────────────────────────────────────────────────────────
#  Tạo mới tiếp đón
# ─────────────────────────────────────────────────────────────
@router.post(
    "",
    response_model=ReceptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo mới tiếp đón",
)
async def create_reception(
    obj_in: ReceptionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Đăng ký lượt khám:
    - Truyền `patient_id` nếu bệnh nhân đã có.
    - Hoặc `patient_data` để tạo bệnh nhân mới đồng thời.
    - visit_time và visit_number tự sinh nếu không truyền.
    """
    if not obj_in.patient_id and not obj_in.patient_data:
        raise HTTPException(status_code=422, detail="Phải cung cấp patient_id hoặc patient_data")

    patient_id = obj_in.patient_id
    if not patient_id and obj_in.patient_data:
        patient, _ = await crud_patient.get_or_create_by_cccd(db, obj_in=obj_in.patient_data)
        patient_id = patient.id

    patient = await crud_patient.get(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh nhân")

    reception = await crud_reception.create_reception(db, obj_in=obj_in, patient_id=patient_id)
    reception_detail = await crud_reception.get_with_patient(db, reception.id)

    stats = await crud_reception.get_today_stats(db)
    await ws_manager.broadcast("reception", {"type": "reception_update", "data": stats})

    return reception_detail


# ─────────────────────────────────────────────────────────────
#  Thống kê
# ─────────────────────────────────────────────────────────────
@router.get(
    "/stats",
    summary="Thống kê tiếp đón hôm nay",
)
async def get_today_stats(db: AsyncSession = Depends(get_db)):
    """Tổng số lượt theo trạng thái (pending / checked_in / completed / cancelled)."""
    return await crud_reception.get_today_stats(db)


@router.get(
    "/clinic-stats",
    response_model=ClinicRoomStatResponse,
    summary="Thống kê theo phòng khám",
)
async def get_clinic_room_stats(
    visit_date: Optional[date] = Query(None, description="Ngày khám, mặc định hôm nay"),
    db: AsyncSession = Depends(get_db),
):
    """
    Bảng thống kê phòng khám: mỗi phòng hiển thị
    Tổng số / Chưa tiếp nhận / BHYT / Dịch vụ.
    Dòng cuối là Tổng cộng.
    """
    raw = await crud_reception.get_clinic_room_stats(db, visit_date=visit_date)
    rooms = [ClinicRoomStat(**r) for r in raw["rooms"]]
    return ClinicRoomStatResponse(
        rooms=rooms,
        total_all=raw["total_all"],
        total_pending=raw["total_pending"],
        total_bhyt=raw["total_bhyt"],
        total_service=raw["total_service"],
    )


# ─────────────────────────────────────────────────────────────
#  Danh sách
# ─────────────────────────────────────────────────────────────
@router.get(
    "",
    response_model=PaginatedResponse[ReceptionList],
    summary="Danh sách tiếp đón",
)
async def list_receptions(
    visit_date:    Optional[date] = Query(None, description="Ngày khám, mặc định hôm nay"),
    status_filter: Optional[str]  = Query(None, alias="status", description="Lọc trạng thái"),
    clinic_room:   Optional[str]  = Query(None, description="Lọc theo phòng khám"),
    page:          int            = Query(1, ge=1),
    page_size:     int            = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    status_enum = None
    if status_filter:
        try:
            status_enum = ReceptionStatus(status_filter.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Trạng thái không hợp lệ: {status_filter}")

    target_date = visit_date or date.today()
    skip = (page - 1) * page_size

    items = await crud_reception.get_by_date(
        db,
        visit_date=target_date,
        status=status_enum,
        clinic_room=clinic_room,
        skip=skip,
        limit=page_size,
    )
    total = await crud_reception.count_by_date(
        db,
        visit_date=target_date,
        status=status_enum,
        clinic_room=clinic_room,
    )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )


# ─────────────────────────────────────────────────────────────
#  Chi tiết / Cập nhật
# ─────────────────────────────────────────────────────────────
@router.get(
    "/{reception_id}",
    response_model=ReceptionResponse,
    summary="Chi tiết tiếp đón",
)
async def get_reception(
    reception_id: int,
    db: AsyncSession = Depends(get_db),
):
    reception = await crud_reception.get_with_patient(db, reception_id)
    if not reception:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin tiếp đón")
    return reception


@router.put(
    "/{reception_id}",
    response_model=ReceptionResponse,
    summary="Cập nhật thông tin tiếp đón",
)
async def update_reception(
    reception_id: int,
    obj_in: ReceptionUpdate,
    db: AsyncSession = Depends(get_db),
):
    reception = await crud_reception.get(db, reception_id)
    if not reception:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin tiếp đón")
    await crud_reception.update_reception(db, db_obj=reception, obj_in=obj_in)
    return await crud_reception.get_with_patient(db, reception_id)


# ─────────────────────────────────────────────────────────────
#  Workflow transitions
# ─────────────────────────────────────────────────────────────
@router.post(
    "/{reception_id}/check-in",
    response_model=ReceptionResponse,
    summary="Check-in bệnh nhân (PENDING → CHECKED_IN)",
)
async def check_in(
    reception_id: int,
    obj_in: ReceptionCheckIn,
    db: AsyncSession = Depends(get_db),
):
    reception = await crud_reception.get(db, reception_id)
    if not reception:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin tiếp đón")

    if reception.status != ReceptionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Chỉ có thể check-in khi trạng thái PENDING (hiện tại: {reception.status.value})",
        )

    if obj_in.queue_ticket_id:
        ticket = await crud_queue_ticket.get(db, obj_in.queue_ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Không tìm thấy số thứ tự")

    await crud_reception.check_in(db, reception=reception, obj_in=obj_in)
    result = await crud_reception.get_with_patient(db, reception_id)

    stats = await crud_reception.get_today_stats(db)
    await ws_manager.broadcast("reception", {"type": "reception_update", "data": stats})

    return result


@router.post(
    "/{reception_id}/complete",
    response_model=ReceptionResponse,
    summary="Hoàn tất tiếp đón",
)
async def complete_reception(
    reception_id: int,
    db: AsyncSession = Depends(get_db),
):
    reception = await crud_reception.get(db, reception_id)
    if not reception:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin tiếp đón")
    await crud_reception.complete_reception(db, reception=reception)
    return await crud_reception.get_with_patient(db, reception_id)


@router.post(
    "/{reception_id}/cancel",
    response_model=ReceptionResponse,
    summary="Huỷ tiếp đón",
)
async def cancel_reception(
    reception_id: int,
    db: AsyncSession = Depends(get_db),
):
    reception = await crud_reception.get(db, reception_id)
    if not reception:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin tiếp đón")
    await crud_reception.cancel_reception(db, reception=reception)
    return await crud_reception.get_with_patient(db, reception_id)
