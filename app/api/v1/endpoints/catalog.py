"""
Catalog endpoints — danh mục dùng chung.

Routes:
  # Thuốc
  GET    /catalog/drugs              — tìm kiếm / danh sách
  POST   /catalog/drugs              — tạo mới (admin)
  GET    /catalog/drugs/{id}         — chi tiết
  PUT    /catalog/drugs/{id}         — cập nhật (admin)
  DELETE /catalog/drugs/{id}         — xoá mềm (admin)

  # Dịch vụ CLS
  GET    /catalog/cls                — tìm kiếm / danh sách
  POST   /catalog/cls                — tạo mới (admin)
  GET    /catalog/cls/{id}           — chi tiết
  PUT    /catalog/cls/{id}           — cập nhật (admin)
  DELETE /catalog/cls/{id}           — xoá mềm (admin)

  # ICD-10
  GET    /catalog/icd10              — tìm kiếm
  GET    /catalog/icd10/{code}       — lấy theo mã
  POST   /catalog/icd10/bulk         — import bulk (admin)
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import require_admin, get_current_user
from app.models.user import User
from app.crud.catalog import crud_drug, crud_cls, crud_icd10, crud_audit
from app.schemas.catalog import (
    DrugCreate, DrugUpdate, DrugResponse, DrugList,
    ClsServiceCreate, ClsServiceUpdate, ClsServiceResponse, ClsServiceList,
    Icd10Response, Icd10BulkRequest,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/catalog", tags=["Catalog - Danh mục"])


# ──────────────────────────────────────────────────────────────────────────────
# THUỐC
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/drugs",
    response_model=PaginatedResponse[DrugList],
    summary="Tìm kiếm danh mục thuốc",
)
async def list_drugs(
    keyword:   str            = Query("", description="Tìm tên / mã / hoạt chất"),
    is_active: Optional[bool] = Query(True),
    is_bhyt:   Optional[bool] = Query(None),
    page:      int            = Query(1, ge=1),
    page_size: int            = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    skip = (page - 1) * page_size
    items, total = await crud_drug.search(
        db, keyword=keyword, is_active=is_active, is_bhyt=is_bhyt,
        skip=skip, limit=page_size,
    )
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=max(1, -(-total // page_size)),
    )


@router.post(
    "/drugs",
    response_model=DrugResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo thuốc mới",
)
async def create_drug(
    body: DrugCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    request: Request = None,
):
    existing = await crud_drug.get_by_code(db, body.drug_code)
    if existing:
        raise HTTPException(409, f"Mã thuốc '{body.drug_code}' đã tồn tại")
    drug = await crud_drug.create_drug(db, obj_in=body)
    await crud_audit.log_change(
        db, user_id=current_user.id, username=current_user.username,
        action="CREATE", table_name="drugs", record_id=drug.id,
        new_data={"drug_code": drug.drug_code, "drug_name": drug.drug_name},
        ip_address=request.client.host if request else None,
        description=f"Tạo thuốc {drug.drug_code} - {drug.drug_name}",
    )
    return drug


@router.get("/drugs/{drug_id}", response_model=DrugResponse, summary="Chi tiết thuốc")
async def get_drug(
    drug_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    drug = await crud_drug.get(db, drug_id)
    if not drug:
        raise HTTPException(404, "Không tìm thấy thuốc")
    return drug


@router.put(
    "/drugs/{drug_id}",
    response_model=DrugResponse,
    summary="Cập nhật thuốc",
)
async def update_drug(
    drug_id: int,
    body: DrugUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    request: Request = None,
):
    drug = await crud_drug.get(db, drug_id)
    if not drug:
        raise HTTPException(404, "Không tìm thấy thuốc")
    old = {"drug_name": drug.drug_name, "unit_price": str(drug.unit_price)}
    drug = await crud_drug.update_drug(db, db_obj=drug, obj_in=body)
    await crud_audit.log_change(
        db, user_id=current_user.id, username=current_user.username,
        action="UPDATE", table_name="drugs", record_id=drug.id,
        old_data=old, new_data=body.model_dump(exclude_none=True),
        ip_address=request.client.host if request else None,
        description=f"Cập nhật thuốc {drug.drug_code}",
    )
    return drug


@router.delete(
    "/drugs/{drug_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá mềm thuốc (is_active=False)",
)
async def deactivate_drug(
    drug_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    request: Request = None,
):
    drug = await crud_drug.get(db, drug_id)
    if not drug:
        raise HTTPException(404, "Không tìm thấy thuốc")
    await crud_drug.update_drug(
        db, db_obj=drug, obj_in=DrugUpdate(is_active=False)
    )
    await crud_audit.log_change(
        db, user_id=current_user.id, username=current_user.username,
        action="DELETE", table_name="drugs", record_id=drug_id,
        old_data={"drug_code": drug.drug_code},
        ip_address=request.client.host if request else None,
        description=f"Vô hiệu hoá thuốc {drug.drug_code}",
    )


# ──────────────────────────────────────────────────────────────────────────────
# DỊCH VỤ CLS
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/cls",
    response_model=PaginatedResponse[ClsServiceList],
    summary="Tìm kiếm danh mục dịch vụ CLS",
)
async def list_cls(
    keyword:       str            = Query(""),
    service_group: Optional[str]  = Query(None),
    is_active:     Optional[bool] = Query(True),
    is_bhyt:       Optional[bool] = Query(None),
    page:          int            = Query(1, ge=1),
    page_size:     int            = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    skip = (page - 1) * page_size
    items, total = await crud_cls.search(
        db, keyword=keyword, service_group=service_group,
        is_active=is_active, is_bhyt=is_bhyt,
        skip=skip, limit=page_size,
    )
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=max(1, -(-total // page_size)),
    )


@router.post(
    "/cls",
    response_model=ClsServiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo dịch vụ CLS mới",
)
async def create_cls(
    body: ClsServiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    request: Request = None,
):
    existing = await crud_cls.get_by_code(db, body.service_code)
    if existing:
        raise HTTPException(409, f"Mã dịch vụ '{body.service_code}' đã tồn tại")
    svc = await crud_cls.create_service(db, obj_in=body)
    await crud_audit.log_change(
        db, user_id=current_user.id, username=current_user.username,
        action="CREATE", table_name="cls_services", record_id=svc.id,
        new_data={"service_code": svc.service_code, "service_name": svc.service_name},
        ip_address=request.client.host if request else None,
        description=f"Tạo dịch vụ CLS {svc.service_code}",
    )
    return svc


@router.get("/cls/{svc_id}", response_model=ClsServiceResponse, summary="Chi tiết dịch vụ CLS")
async def get_cls(
    svc_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = await crud_cls.get(db, svc_id)
    if not svc:
        raise HTTPException(404, "Không tìm thấy dịch vụ CLS")
    return svc


@router.put(
    "/cls/{svc_id}",
    response_model=ClsServiceResponse,
    summary="Cập nhật dịch vụ CLS",
)
async def update_cls(
    svc_id: int,
    body: ClsServiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    request: Request = None,
):
    svc = await crud_cls.get(db, svc_id)
    if not svc:
        raise HTTPException(404, "Không tìm thấy dịch vụ CLS")
    old = {"service_name": svc.service_name, "unit_price": str(svc.unit_price)}
    svc = await crud_cls.update_service(db, db_obj=svc, obj_in=body)
    await crud_audit.log_change(
        db, user_id=current_user.id, username=current_user.username,
        action="UPDATE", table_name="cls_services", record_id=svc.id,
        old_data=old, new_data=body.model_dump(exclude_none=True),
        ip_address=request.client.host if request else None,
        description=f"Cập nhật dịch vụ {svc.service_code}",
    )
    return svc


@router.delete(
    "/cls/{svc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá mềm dịch vụ CLS",
)
async def deactivate_cls(
    svc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    request: Request = None,
):
    svc = await crud_cls.get(db, svc_id)
    if not svc:
        raise HTTPException(404, "Không tìm thấy dịch vụ CLS")
    await crud_cls.update_service(
        db, db_obj=svc, obj_in=ClsServiceUpdate(is_active=False)
    )
    await crud_audit.log_change(
        db, user_id=current_user.id, username=current_user.username,
        action="DELETE", table_name="cls_services", record_id=svc_id,
        old_data={"service_code": svc.service_code},
        ip_address=request.client.host if request else None,
        description=f"Vô hiệu hoá dịch vụ {svc.service_code}",
    )


# ──────────────────────────────────────────────────────────────────────────────
# ICD-10
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/icd10",
    response_model=List[Icd10Response],
    summary="Tìm kiếm mã bệnh ICD-10",
)
async def search_icd10(
    keyword:  str = Query(..., min_length=1, description="Mã hoặc tên bệnh"),
    limit:    int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await crud_icd10.search(db, keyword=keyword, limit=limit)


@router.get(
    "/icd10/{code}",
    response_model=Icd10Response,
    summary="Lấy ICD-10 theo mã",
)
async def get_icd10(
    code: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    icd = await crud_icd10.get_by_code(db, code.upper())
    if not icd:
        raise HTTPException(404, f"Không tìm thấy mã ICD-10: {code}")
    return icd


@router.post(
    "/icd10/bulk",
    summary="Import bulk danh mục ICD-10",
    status_code=status.HTTP_201_CREATED,
)
async def bulk_import_icd10(
    body: Icd10BulkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    request: Request = None,
):
    """Import / upsert danh sách ICD-10 từ file. Trả về số dòng đã xử lý."""
    count = await crud_icd10.bulk_upsert(db, items=body.items)
    await crud_audit.log_change(
        db, user_id=current_user.id, username=current_user.username,
        action="CREATE", table_name="icd10",
        ip_address=request.client.host if request else None,
        description=f"Import bulk {count} mã ICD-10",
    )
    return {"imported": count}
