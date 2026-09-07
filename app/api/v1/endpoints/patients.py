"""
API endpoints quản lý bệnh nhân.

Routes:
  GET    /patients              — Danh sách / tìm kiếm (hỗ trợ keyword)
  POST   /patients              — Tạo mới (sinh patient_code tự động)
  GET    /patients/cccd/{cccd}  — Tra cứu theo CCCD
  GET    /patients/{id}         — Chi tiết đầy đủ
  PUT    /patients/{id}         — Cập nhật thông tin
  GET    /patients/{id}/history — Lịch sử khám
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
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
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
    """Tạo bệnh nhân mới. patient_code tự sinh dạng BNYYYYnnnn."""
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
    """Dùng khi quét CCCD/CMND. Trả 404 nếu chưa có trong hệ thống."""
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
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    patient = await crud_patient.get(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh nhân")
    return await crud_reception.get_by_patient(db, patient_id, skip=skip, limit=limit)
