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


@router.post(
    "/eligibility/{reception_id}",
    response_model=EligibilityResponse,
    summary="Kiểm tra quyền lợi BHYT",
    description=(
        "Xác thực thẻ BHYT cho một lượt tiếp đón, kiểm tra tính hợp lệ và trả về thông tin "
        "đầy đủ về thời hạn, mức hưởng và trạng thái bảo hiểm."
    ),
    responses={
        200: {"description": "Kết quả kiểm tra thẻ BHYT đã được xác thực."},
        404: {"description": "Không tìm thấy lượt tiếp đón tương ứng."},
        422: {"description": "Dữ liệu thẻ BHYT không hợp lệ hoặc không thể xác minh."},
    },
)
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


@router.post(
    "/claims/by-bill/{bill_id}",
    response_model=ClaimResponse,
    summary="Tạo hồ sơ yêu cầu thanh toán BHYT",
    description=(
        "Tạo hồ sơ yêu cầu thanh toán theo hóa đơn đã phát sinh, chuẩn bị dữ liệu BHYT và "
        "chuẩn bị cho bước nộp lên hệ thống bảo hiểm."
    ),
    responses={
        200: {"description": "Hồ sơ yêu cầu BHYT đã được tạo thành công."},
        404: {"description": "Không tìm thấy hóa đơn tương ứng."},
        422: {"description": "Hóa đơn không đủ điều kiện để tạo hồ sơ BHYT."},
    },
)
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


@router.post(
    "/claims/{claim_id}/submit",
    response_model=ClaimResponse,
    summary="Nộp hồ sơ BHYT",
    description=(
        "Gửi hồ sơ BHYT đã được chuẩn bị lên hệ thống bảo hiểm. Việc nộp sẽ cập nhật trạng thái "
        "và lưu mã tham chiếu từ bên cung cấp dịch vụ."
    ),
    responses={
        200: {"description": "Hồ sơ đã được nộp thành công."},
        404: {"description": "Không tìm thấy hồ sơ BHYT."},
        409: {"description": "Hồ sơ đang ở trạng thái không cho phép nộp lại."},
    },
)
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


@router.post(
    "/claims/{claim_id}/reconcile",
    response_model=ClaimResponse,
    summary="Đối soát kết quả thanh toán BHYT",
    description=(
        "Nhận kết quả đối soát từ hệ thống BHYT, cập nhật số tiền chấp nhận và từ chối, cũng như "
        "lưu thông tin phản hồi phục vụ kiểm tra và báo cáo."
    ),
    responses={
        200: {"description": "Đối soát thành công và hồ sơ được cập nhật."},
        404: {"description": "Không tìm thấy hồ sơ BHYT."},
        409: {"description": "Kết quả đối soát không hợp lệ hoặc trạng thái hồ sơ không cho phép cập nhật."},
    },
)
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
