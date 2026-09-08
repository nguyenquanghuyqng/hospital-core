"""
API endpoints quản lý hồ sơ bệnh nhân.

Routes:
  GET    /patients                — Danh sách / tìm kiếm bệnh nhân (phân trang)
  POST   /patients                — Tạo mới bệnh nhân (sinh patient_code tự động)
  GET    /patients/cccd/{cccd}    — Tra cứu theo số CCCD/CMND
  GET    /patients/{id}           — Chi tiết đầy đủ một bệnh nhân
  PUT    /patients/{id}           — Cập nhật thông tin bệnh nhân
  GET    /patients/{id}/history   — Lịch sử các lượt khám của bệnh nhân
"""
from typing import Optional
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.crud.patient import crud_patient
from app.crud.reception import crud_reception
from app.schemas.patient import PatientCreate, PatientUpdate, PatientResponse, PatientList
from app.schemas.reception import ReceptionList
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/patients", tags=["Patients - Bệnh nhân"])


@router.get(
    "",
    response_model=PaginatedResponse[PatientList],
    summary="Danh sách / tìm kiếm bệnh nhân",
)
async def list_patients(
    keyword: Optional[str] = Query(None, description="Tìm theo tên, CCCD, SĐT, mã BN"),
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy danh sách bệnh nhân có phân trang, tuỳ chọn tìm kiếm theo từ khoá.

    Khi ``keyword`` được cung cấp, tìm kiếm case-insensitive trên:
    họ tên, số CCCD, số điện thoại, và mã bệnh nhân.
    Khi không có ``keyword``, trả toàn bộ danh sách sắp xếp theo ID mới nhất.

    Args:
        keyword: Từ khoá tìm kiếm (tuỳ chọn).
        page: Số trang hiện tại (bắt đầu từ 1).
        page_size: Số bản ghi mỗi trang (1–100).
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.common.PaginatedResponse` chứa danh sách
        :class:`~app.schemas.patient.PatientList`.
    """
    skip = (page - 1) * page_size
    if keyword:
        items = await crud_patient.search(db, keyword=keyword, skip=skip, limit=page_size)
        total = await crud_patient.count_search(db, keyword)
    else:
        items = await crud_patient.get_multi(db, skip=skip, limit=page_size)
        total = await crud_patient.count(db)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo mới bệnh nhân",
)
async def create_patient(
    obj_in: PatientCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Tạo hồ sơ bệnh nhân mới trong hệ thống.

    ``patient_code`` được tự sinh dạng ``BNYYYYnnnn`` — không cần truyền từ client.
    ``birth_year`` được tự đồng bộ từ ``date_of_birth`` nếu không truyền.

    Args:
        obj_in: :class:`~app.schemas.patient.PatientCreate` chứa dữ liệu bệnh nhân.
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.patient.PatientResponse` của bệnh nhân vừa tạo.

    Raises:
        HTTPException 409: CCCD đã tồn tại trong hệ thống.
    """
    if obj_in.cccd:
        existing = await crud_patient.get_by_cccd(db, obj_in.cccd)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"CCCD {obj_in.cccd} đã tồn tại (Mã BN: {existing.patient_code or existing.id})",
            )
    return await crud_patient.create_patient(db, obj_in=obj_in)


@router.get(
    "/cccd/{cccd}",
    response_model=PatientResponse,
    summary="Tra cứu bệnh nhân theo CCCD",
)
async def get_patient_by_cccd(
    cccd: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Tra cứu bệnh nhân theo số CCCD/CMND.

    Dùng khi quét thẻ căn cước tại quầy tiếp đón để kiểm tra bệnh nhân
    đã có trong hệ thống chưa trước khi tạo mới.

    Args:
        cccd: Số CCCD hoặc CMND cần tra cứu.
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.patient.PatientResponse` nếu tìm thấy.

    Raises:
        HTTPException 404: Chưa có bệnh nhân với CCCD này trong hệ thống.
    """
    patient = await crud_patient.get_by_cccd(db, cccd)
    if not patient:
        raise HTTPException(status_code=404, detail="Chưa có bệnh nhân với CCCD này")
    return patient


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Chi tiết bệnh nhân",
)
async def get_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy toàn bộ thông tin hành chính của một bệnh nhân theo ID.

    Args:
        patient_id: ID bệnh nhân cần xem.
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.patient.PatientResponse` với đầy đủ thông tin.

    Raises:
        HTTPException 404: Không tìm thấy bệnh nhân với ID này.
    """
    patient = await crud_patient.get(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh nhân")
    return patient


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Cập nhật thông tin bệnh nhân",
)
async def update_patient(
    patient_id: int,
    obj_in: PatientUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Cập nhật thông tin hành chính của bệnh nhân (partial update).

    Chỉ các fields được truyền vào mới được cập nhật.
    Nếu ``date_of_birth`` thay đổi, ``birth_year`` sẽ được tự đồng bộ.
    Kiểm tra CCCD mới không trùng với bệnh nhân khác trước khi lưu.

    Args:
        patient_id: ID bệnh nhân cần cập nhật.
        obj_in: :class:`~app.schemas.patient.PatientUpdate` chứa dữ liệu mới.
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.patient.PatientResponse` sau khi cập nhật.

    Raises:
        HTTPException 404: Không tìm thấy bệnh nhân.
        HTTPException 409: CCCD mới đã được sử dụng bởi bệnh nhân khác.
    """
    patient = await crud_patient.get(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh nhân")

    if obj_in.cccd and obj_in.cccd != patient.cccd:
        existing = await crud_patient.get_by_cccd(db, obj_in.cccd)
        if existing:
            raise HTTPException(status_code=409, detail=f"CCCD {obj_in.cccd} đã được sử dụng")

    return await crud_patient.update_patient(db, db_obj=patient, obj_in=obj_in)


@router.get(
    "/{patient_id}/history",
    response_model=list[ReceptionList],
    summary="Lịch sử khám của bệnh nhân",
)
async def get_patient_history(
    patient_id: int,
    skip:  int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy danh sách các lượt đăng ký khám của một bệnh nhân, mới nhất trước.

    Args:
        patient_id: ID bệnh nhân cần xem lịch sử.
        skip: Offset phân trang.
        limit: Số bản ghi tối đa trả về.
        db: Async database session (injected).

    Returns:
        Danh sách :class:`~app.schemas.reception.ReceptionList`.

    Raises:
        HTTPException 404: Không tìm thấy bệnh nhân.
    """
    patient = await crud_patient.get(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh nhân")
    return await crud_reception.get_by_patient(db, patient_id, skip=skip, limit=limit)
