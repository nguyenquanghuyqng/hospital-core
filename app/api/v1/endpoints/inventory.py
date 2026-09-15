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


@router.post("/batches/receive", response_model=DrugBatchResponse, status_code=status.HTTP_201_CREATED)
async def receive_batch(
    body: BatchReceive,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        return await crud_inventory.receive(db, body, current_user.id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/batches/adjust", response_model=DrugBatchResponse)
async def adjust_batch(
    body: BatchAdjust,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        return await crud_inventory.adjust(db, body, current_user.id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/dispense", response_model=list[DrugBatchResponse])
async def dispense_drug(
    body: BatchDispense,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    try:
        return await crud_inventory.dispense(db, body, current_user.id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/drugs/{drug_id}/batches", response_model=list[DrugBatchResponse])
async def list_batches(
    drug_id: int,
    include_expired: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_clinical),
):
    return await crud_inventory.list_batches(db, drug_id, include_expired)


@router.get("/transactions", response_model=list[InventoryTransactionResponse])
async def list_transactions(
    drug_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_clinical),
):
    return await crud_inventory.list_transactions(db, drug_id, limit)
