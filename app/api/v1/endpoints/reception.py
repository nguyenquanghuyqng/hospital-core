"""
API endpoints quản lý tiếp đón bệnh nhân.

Routes:
  POST   /receptions/scan-cccd           — Quét CCCD → tra cứu hoặc tạo mới bệnh nhân
  POST   /receptions                     — Tạo mới lượt tiếp đón
  GET    /receptions/stats               — Thống kê hôm nay theo trạng thái
  GET    /receptions/clinic-stats        — Thống kê theo phòng khám
  GET    /receptions                     — Danh sách lượt tiếp đón (phân trang, lọc)
  GET    /receptions/{id}                — Chi tiết lượt tiếp đón
  PUT    /receptions/{id}                — Cập nhật thông tin
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
from app.core.deps import require_receptionist
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

router = APIRouter(
    prefix="/receptions",
    tags=["Reception - Tiếp đón"],
    dependencies=[Depends(require_receptionist)],
)


# ── Local schemas ─────────────────────────────────────────────────────────────

class ScanCCCDRequest(PatientCreate):
    """
    Body request khi quét CCCD: dữ liệu đọc từ chip hoặc barcode.

    Kế thừa :class:`~app.schemas.patient.PatientCreate` —
    truyền toàn bộ thông tin đọc được từ thẻ căn cước.
    """
    pass


class ScanCCCDResponse(BaseModel):
    """
    Response sau khi quét CCCD.

    Attributes:
        patient: Thông tin bệnh nhân (đã có hoặc vừa tạo mới).
        is_new_patient: ``True`` nếu bệnh nhân vừa được tạo mới.
        message: Thông báo kết quả cho nhân viên tiếp đón.
    """

    patient: PatientResponse
    is_new_patient: bool
    message: str

    model_config = {"from_attributes": True}


# ── Scan CCCD ─────────────────────────────────────────────────────────────────

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
    Xử lý dữ liệu quét CCCD/CMND từ thiết bị đọc thẻ.

    Logic upsert:
    - Bệnh nhân đã có trong hệ thống (tra theo CCCD) → trả về thông tin hiện có.
    - Chưa có → tạo mới từ dữ liệu CCCD, sinh ``patient_code`` tự động.

    Args:
        obj_in: :class:`ScanCCCDRequest` chứa dữ liệu đọc từ thẻ CCCD.
        db: Async database session (injected).

    Returns:
        :class:`ScanCCCDResponse` với thông tin bệnh nhân và cờ ``is_new_patient``.
    """
    patient, is_new = await crud_patient.get_or_create_by_cccd(db, obj_in=obj_in)
    return ScanCCCDResponse(
        patient=patient,
        is_new_patient=is_new,
        message="Bệnh nhân mới — đã thêm vào hệ thống" if is_new else "Bệnh nhân đã có trong hệ thống",
    )


# ── Tạo mới tiếp đón ─────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ReceptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo mới lượt tiếp đón",
)
async def create_reception(
    obj_in: ReceptionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Đăng ký lượt khám mới cho bệnh nhân.

    Có thể dùng theo hai cách:
    - Truyền ``patient_id`` nếu bệnh nhân đã có trong hệ thống.
    - Truyền ``patient_data`` để tạo bệnh nhân mới đồng thời.

    ``visit_time`` và ``visit_number`` tự sinh nếu không truyền.
    Sau khi tạo, broadcast cập nhật stats tới quầy tiếp đón qua WebSocket.

    Args:
        obj_in: :class:`~app.schemas.reception.ReceptionCreate`.
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.reception.ReceptionResponse` kèm thông tin bệnh nhân.

    Raises:
        HTTPException 422: Không cung cấp ``patient_id`` lẫn ``patient_data``.
        HTTPException 404: Không tìm thấy bệnh nhân với ``patient_id`` đã cho.
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


# ── Thống kê ─────────────────────────────────────────────────────────────────

@router.get("/stats", summary="Thống kê tiếp đón hôm nay")
async def get_today_stats(db: AsyncSession = Depends(get_db)):
    """
    Tổng số lượt tiếp đón hôm nay phân theo trạng thái.

    Trả về: ``pending``, ``checked_in``, ``completed``, ``cancelled``, ``total``.

    Args:
        db: Async database session (injected).

    Returns:
        Dict thống kê theo trạng thái của ngày hiện tại.
    """
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
    Bảng thống kê số lượt khám theo từng phòng khám trong ngày.

    Mỗi phòng hiển thị: Tổng / Chưa tiếp nhận / BHYT / Dịch vụ.
    Dòng cuối là tổng cộng toàn bệnh viện.

    Args:
        visit_date: Ngày cần thống kê (mặc định hôm nay).
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.reception.ClinicRoomStatResponse`.
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


# ── Danh sách ─────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=PaginatedResponse[ReceptionList],
    summary="Danh sách lượt tiếp đón",
)
async def list_receptions(
    visit_date:    Optional[date] = Query(None, description="Ngày khám, mặc định hôm nay"),
    status_filter: Optional[str]  = Query(None, alias="status", description="Lọc trạng thái"),
    clinic_room:   Optional[str]  = Query(None, description="Lọc theo phòng khám"),
    page:          int            = Query(1, ge=1),
    page_size:     int            = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy danh sách lượt tiếp đón có phân trang, tuỳ chọn lọc.

    Kết quả sắp xếp: ưu tiên cao → số khám tăng dần → ID tăng dần.

    Args:
        visit_date: Ngày khám (mặc định hôm nay).
        status_filter: Lọc theo trạng thái (VD: ``"pending"``, ``"checked_in"``).
        clinic_room: Lọc theo tên phòng khám.
        page: Số trang (bắt đầu từ 1).
        page_size: Số bản ghi mỗi trang (1–100).
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.common.PaginatedResponse` chứa
        danh sách :class:`~app.schemas.reception.ReceptionList`.

    Raises:
        HTTPException 400: Giá trị ``status`` không hợp lệ.
    """
    status_enum = None
    if status_filter:
        try:
            status_enum = ReceptionStatus(status_filter.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Trạng thái không hợp lệ: {status_filter}")

    target_date = visit_date or date.today()
    skip = (page - 1) * page_size

    items = await crud_reception.get_by_date(
        db, visit_date=target_date, status=status_enum,
        clinic_room=clinic_room, skip=skip, limit=page_size,
    )
    total = await crud_reception.count_by_date(
        db, visit_date=target_date, status=status_enum, clinic_room=clinic_room,
    )

    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )


# ── Chi tiết / Cập nhật ───────────────────────────────────────────────────────

@router.get(
    "/{reception_id}",
    response_model=ReceptionResponse,
    summary="Chi tiết lượt tiếp đón",
)
async def get_reception(
    reception_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy thông tin đầy đủ một lượt tiếp đón kèm thông tin bệnh nhân.

    Args:
        reception_id: ID lượt tiếp đón.
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.reception.ReceptionResponse`.

    Raises:
        HTTPException 404: Không tìm thấy lượt tiếp đón.
    """
    reception = await crud_reception.get_with_patient(db, reception_id)
    if not reception:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin tiếp đón")
    return reception


@router.put(
    "/{reception_id}",
    response_model=ReceptionResponse,
    summary="Cập nhật thông tin lượt tiếp đón",
)
async def update_reception(
    reception_id: int,
    obj_in: ReceptionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Cập nhật thông tin hành chính / bảo hiểm của lượt tiếp đón (partial update).

    Không thể thay đổi ``status`` qua endpoint này — dùng workflow endpoints.

    Args:
        reception_id: ID lượt tiếp đón cần cập nhật.
        obj_in: :class:`~app.schemas.reception.ReceptionUpdate`.
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.reception.ReceptionResponse` sau khi cập nhật.

    Raises:
        HTTPException 404: Không tìm thấy lượt tiếp đón.
    """
    reception = await crud_reception.get(db, reception_id)
    if not reception:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin tiếp đón")
    await crud_reception.update_reception(db, db_obj=reception, obj_in=obj_in)
    return await crud_reception.get_with_patient(db, reception_id)


# ── Workflow transitions ──────────────────────────────────────────────────────

@router.post(
    "/{reception_id}/check-in",
    response_model=ReceptionResponse,
    summary="Check-in bệnh nhân (PENDING/CHECKED_IN → CHECKED_IN)",
)
async def check_in(
    reception_id: int,
    obj_in: ReceptionCheckIn,
    db: AsyncSession = Depends(get_db),
):
    """
    Xác nhận bệnh nhân đã có mặt trong danh sách chờ khám.

    Với flow mới, bệnh nhân được đăng ký đã lập tức ở trạng thái CHECKED_IN,
    nên endpoint này hoạt động như thao tác idempotent nếu lượt tiếp đón đã có STT.

    Args:
        reception_id: ID lượt tiếp đón cần check-in.
        obj_in: :class:`~app.schemas.reception.ReceptionCheckIn`.
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.reception.ReceptionResponse` với status CHECKED_IN.

    Raises:
        HTTPException 404: Không tìm thấy lượt tiếp đón hoặc số thứ tự.
        HTTPException 400: Lượt tiếp đón không ở trạng thái PENDING hoặc CHECKED_IN.
    """
    reception = await crud_reception.get(db, reception_id)
    if not reception:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin tiếp đón")

    if reception.status not in (ReceptionStatus.PENDING, ReceptionStatus.CHECKED_IN):
        raise HTTPException(
            status_code=400,
            detail=f"Không thể check-in khi trạng thái hiện tại là {reception.status.value}",
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
    summary="Hoàn tất lượt tiếp đón",
)
async def complete_reception(
    reception_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Chuyển lượt tiếp đón sang COMPLETED (hoàn tất).

    Args:
        reception_id: ID lượt tiếp đón cần hoàn tất.
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.reception.ReceptionResponse` với status COMPLETED.

    Raises:
        HTTPException 404: Không tìm thấy lượt tiếp đón.
    """
    reception = await crud_reception.get(db, reception_id)
    if not reception:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin tiếp đón")
    await crud_reception.complete_reception(db, reception=reception)
    return await crud_reception.get_with_patient(db, reception_id)


@router.post(
    "/{reception_id}/cancel",
    response_model=ReceptionResponse,
    summary="Huỷ lượt tiếp đón",
)
async def cancel_reception(
    reception_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Huỷ lượt tiếp đón (→ CANCELLED).

    Args:
        reception_id: ID lượt tiếp đón cần huỷ.
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.reception.ReceptionResponse` với status CANCELLED.

    Raises:
        HTTPException 404: Không tìm thấy lượt tiếp đón.
    """
    reception = await crud_reception.get(db, reception_id)
    if not reception:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin tiếp đón")
    await crud_reception.cancel_reception(db, reception=reception)
    return await crud_reception.get_with_patient(db, reception_id)
