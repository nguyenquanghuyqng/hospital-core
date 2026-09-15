"""Batch and expiry-aware drug inventory endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin, require_cashier, require_clinical
from app.crud.inventory import crud_inventory
from app.db.session import get_db
from app.models.user import User
from app.schemas.inventory import (
    BatchAdjust, BatchDispense, BatchReceive,
    DrugBatchResponse, InventoryTransactionResponse,
)

router = APIRouter(prefix="/inventory", tags=["Inventory - Kho thuốc"])


@router.post(
    "/batches/receive",
    response_model=DrugBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Nhập lô thuốc mới",
    description=(
        "Nhận thuốc vào kho với số lô, ngày hết hạn và thông tin nhà cung cấp. "
        "API này cập nhật tồn kho hiện có và tạo lịch sử nhập hàng theo lô thuốc."
    ),
    responses={
        201: {"description": "Lô thuốc đã được nhập kho thành công."},
        422: {"description": "Dữ liệu nhập kho không hợp lệ hoặc thuốc không tồn tại."},
    },
)
async def receive_batch(
    body: BatchReceive,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        return await crud_inventory.receive(db, body, current_user.id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/batches/adjust",
    response_model=DrugBatchResponse,
    summary="Điều chỉnh tồn kho theo lô",
    description=(
        "Cập nhật số lượng hiện có của một lô thuốc theo kiểm kê, điều chỉnh sai lệch hoặc xử lý "
        "mất hàng, hao hụt, kiểm kê đầu kỳ."
    ),
    responses={
        200: {"description": "Lô thuốc đã được cập nhật tồn kho."},
        422: {"description": "Số lượng hoặc lý do điều chỉnh không hợp lệ."},
    },
)
async def adjust_batch(
    body: BatchAdjust,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        return await crud_inventory.adjust(db, body, current_user.id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/dispense",
    response_model=list[DrugBatchResponse],
    summary="Xuất thuốc cho bệnh nhân hoặc hồ sơ điều trị",
    description=(
        "Xuất thuốc theo đơn thuốc hoặc hồ sơ điều trị, đồng thời trừ tồn kho phù hợp với nguồn phát sinh "
        "và lưu lịch sử giao dịch kho."
    ),
    responses={
        200: {"description": "Xuất thuốc thành công và tồn kho đã được trừ."},
        409: {"description": "Không đủ thuốc hoặc dữ liệu nguồn phát sinh không hợp lệ."},
    },
)
async def dispense_drug(
    body: BatchDispense,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    try:
        return await crud_inventory.dispense(db, body, current_user.id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/drugs/{drug_id}/batches",
    response_model=list[DrugBatchResponse],
    summary="Danh sách lô thuốc theo thuốc",
    description=(
        "Trả về toàn bộ lô thuốc của một thuốc, bao gồm hàng còn khả dụng và có thể bật tùy chọn "
        "hiển thị cả lô đã hết hạn."
    ),
    responses={
        200: {"description": "Danh sách các lô thuốc của thuốc được trả về."},
    },
)
async def list_batches(
    drug_id: int,
    include_expired: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_clinical),
):
    return await crud_inventory.list_batches(db, drug_id, include_expired)


@router.get(
    "/transactions",
    response_model=list[InventoryTransactionResponse],
    summary="Lịch sử giao dịch kho",
    description=(
        "Hiển thị lịch sử nhập, điều chỉnh, xuất thuốc và các giao dịch kho gần nhất, phục vụ kiểm toán "
        "và theo dõi tồn kho."
    ),
    responses={
        200: {"description": "Danh sách giao dịch kho được trả về."},
    },
)
async def list_transactions(
    drug_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_clinical),
):
    return await crud_inventory.list_transactions(db, drug_id, limit)
