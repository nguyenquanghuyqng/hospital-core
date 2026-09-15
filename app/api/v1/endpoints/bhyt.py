"""BHYT eligibility, claim submission, and reconciliation endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import require_cashier
from app.crud.billing import crud_bill
from app.db.session import get_db
from app.models.billing import Bill
from app.models.reception import Reception
from app.models.user import User
from app.models.bhyt import BhytClaim
from app.schemas.bhyt import EligibilityRequest, EligibilityResponse, ClaimResponse, ReconciliationRequest
from app.services.bhyt_claim_service import check_eligibility, prepare_claim, submit_claim, reconcile_claim

router = APIRouter(prefix="/bhyt", tags=["BHYT - Eligibility and Claims"])


@router.post("/eligibility/{reception_id}", response_model=EligibilityResponse)
async def verify_eligibility(
    reception_id: int,
    body: EligibilityRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    reception = await db.scalar(select(Reception).where(Reception.id == reception_id))
    if not reception:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt tiếp đón")
    try:
        return await check_eligibility(db, reception, body.insurance_number, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/claims/by-bill/{bill_id}", response_model=ClaimResponse)
async def create_claim(
    bill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    bill = await crud_bill.get_full(db, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Không tìm thấy hóa đơn")
    try:
        return await prepare_claim(db, bill, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/claims/{claim_id}/submit", response_model=ClaimResponse)
async def submit_claim_endpoint(
    claim_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    claim = await db.scalar(select(BhytClaim).where(BhytClaim.id == claim_id))
    if not claim:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ BHYT")
    try:
        return await submit_claim(db, claim)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/claims/{claim_id}/reconcile", response_model=ClaimResponse)
async def reconcile_claim_endpoint(
    claim_id: int,
    body: ReconciliationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    claim = await db.scalar(select(BhytClaim).where(BhytClaim.id == claim_id))
    if not claim:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ BHYT")
    try:
        return await reconcile_claim(
            db, claim, body.status, body.accepted_amount,
            body.rejected_amount, body.external_ref, body.response_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
