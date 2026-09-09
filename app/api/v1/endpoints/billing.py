"""
Billing endpoints — viện phí và thanh toán.

Tất cả mutation yêu cầu role ``cashier`` hoặc ``admin``.
GET có thể truy cập với role ``doctor`` hoặc ``nurse``.

Routes:
  POST   /billing/bills                       — Tạo hóa đơn từ phiếu khám
  GET    /billing/bills                       — Danh sách hóa đơn (filter theo status)
  GET    /billing/bills/by-exam/{exam_id}     — Hóa đơn của phiếu khám
  GET    /billing/bills/{id}                  — Chi tiết hóa đơn
  PUT    /billing/bills/{id}                  — Cập nhật hóa đơn (trước khi phát hành)
  POST   /billing/bills/{id}/issue            — Phát hành hóa đơn (DRAFT → ISSUED)
  POST   /billing/bills/{id}/payment          — Ghi nhận thanh toán
  POST   /billing/bills/{id}/cancel           — Huỷ hóa đơn
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import require_cashier, require_clinical, get_current_user
from app.models.user import User
from app.models.enums import BillStatus, ExaminationStatus
from app.models.examination import Examination
from app.crud.billing import crud_bill
from app.crud.catalog import crud_audit
from app.schemas.billing import (
    BillCreate, BillUpdate, BillResponse, BillSummary,
    PaymentCreate, PaymentResponse,
)
from sqlalchemy import select

router = APIRouter(prefix="/billing", tags=["Billing - Viện phí & Thanh toán"])


async def _get_bill_or_404(db: AsyncSession, bill_id: int) -> object:
    bill = await crud_bill.get_full(db, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Không tìm thấy hóa đơn")
    return bill


# ── Tạo và tra cứu ────────────────────────────────────────────────────────────

@router.post(
    "/bills",
    response_model=BillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo hóa đơn từ phiếu khám",
)
async def create_bill(
    obj_in: BillCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    """
    Thu ngân tạo hóa đơn viện phí từ phiếu khám đã COMPLETED.

    Tự động sinh BillItems từ tất cả PrescriptionItems của phiếu.
    Kiểm tra idempotency: mỗi phiếu khám chỉ có một hóa đơn.

    Raises:
        404: Phiếu khám không tồn tại.
        400: Phiếu chưa hoàn tất hoặc đã có hóa đơn.
    """
    # Kiểm tra phiếu khám
    exam_row = await db.execute(
        select(Examination).where(Examination.id == obj_in.examination_id)
    )
    exam = exam_row.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu khám")
    if exam.status != ExaminationStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Phiếu khám phải ở trạng thái COMPLETED mới tạo được hóa đơn",
        )

    # Idempotency
    existing = await crud_bill.get_by_examination(db, obj_in.examination_id)
    if existing:
        return existing

    bill = await crud_bill.create_from_examination(
        db,
        obj_in=obj_in,
        cashier_id=current_user.id,
        cashier_name=current_user.full_name or current_user.username,
    )
    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="CREATE",
        table_name="bills",
        record_id=bill.id,
        new_data={"bill_number": bill.bill_number, "grand_total": str(bill.grand_total)},
        description=f"Tạo hóa đơn {bill.bill_number}",
    )
    await db.commit()
    return bill


@router.get(
    "/bills",
    response_model=List[BillSummary],
    summary="Danh sách hóa đơn",
)
async def list_bills(
    status_filter: Optional[BillStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    items, _ = await crud_bill.list_bills(db, status=status_filter, skip=skip, limit=limit)
    return items


@router.get(
    "/bills/by-exam/{examination_id}",
    response_model=BillResponse,
    summary="Hóa đơn của phiếu khám",
)
async def get_bill_by_exam(
    examination_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_clinical),
):
    bill = await crud_bill.get_by_examination(db, examination_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Chưa có hóa đơn cho phiếu khám này")
    return bill


@router.get(
    "/bills/{bill_id}",
    response_model=BillResponse,
    summary="Chi tiết hóa đơn",
)
async def get_bill(
    bill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_clinical),
):
    return await _get_bill_or_404(db, bill_id)


# ── Cập nhật ───────────────────────────────────────────────────────────────────

@router.put(
    "/bills/{bill_id}",
    response_model=BillResponse,
    summary="Cập nhật hóa đơn",
)
async def update_bill(
    bill_id: int,
    obj_in: BillUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    """Chỉ cập nhật được khi hóa đơn ở trạng thái DRAFT."""
    bill = await _get_bill_or_404(db, bill_id)
    if bill.status not in (BillStatus.DRAFT, BillStatus.ISSUED):
        raise HTTPException(status_code=400, detail="Không thể cập nhật hóa đơn đã thanh toán")
    updated = await crud_bill.update_bill(db, db_obj=bill, obj_in=obj_in)
    await db.commit()
    return updated


# ── Workflow ───────────────────────────────────────────────────────────────────

@router.post(
    "/bills/{bill_id}/issue",
    response_model=BillResponse,
    summary="Phát hành hóa đơn (DRAFT → ISSUED)",
)
async def issue_bill(
    bill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    """Phát hành hóa đơn — bệnh nhân bắt đầu có thể thanh toán."""
    bill = await _get_bill_or_404(db, bill_id)
    if bill.status != BillStatus.DRAFT:
        raise HTTPException(status_code=400,
                            detail=f"Hóa đơn đang ở trạng thái {bill.status.value}, không thể phát hành")
    issued = await crud_bill.issue_bill(db, db_obj=bill)
    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="UPDATE",
        table_name="bills",
        record_id=bill_id,
        new_data={"status": "issued"},
        description=f"Phát hành hóa đơn {issued.bill_number}",
    )
    await db.commit()
    return issued


@router.post(
    "/bills/{bill_id}/payment",
    response_model=BillResponse,
    summary="Ghi nhận thanh toán",
)
async def add_payment(
    bill_id: int,
    obj_in: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    """
    Thu ngân ghi nhận một lần thanh toán.
    Tự động chuyển bill → PARTIAL hoặc PAID tùy số tiền còn lại.
    """
    bill = await _get_bill_or_404(db, bill_id)
    if bill.status not in (BillStatus.ISSUED, BillStatus.PARTIAL):
        raise HTTPException(
            status_code=400,
            detail=f"Hóa đơn phải ở trạng thái ISSUED hoặc PARTIAL (hiện: {bill.status.value})",
        )
    updated = await crud_bill.add_payment(
        db, db_obj=bill, obj_in=obj_in, cashier_id=current_user.id
    )
    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="CREATE",
        table_name="payments",
        record_id=bill_id,
        new_data={
            "amount": str(obj_in.amount),
            "method": obj_in.payment_method.value,
            "bill_status": updated.status.value,
        },
        description=f"Thanh toán {obj_in.amount:,.0f}đ cho hóa đơn {updated.bill_number}",
    )
    await db.commit()
    return updated


@router.post(
    "/bills/{bill_id}/cancel",
    response_model=BillResponse,
    summary="Huỷ hóa đơn",
)
async def cancel_bill(
    bill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    bill = await _get_bill_or_404(db, bill_id)
    if bill.status == BillStatus.PAID:
        raise HTTPException(status_code=400,
                            detail="Không thể huỷ hóa đơn đã thanh toán. Dùng chức năng hoàn tiền.")
    cancelled = await crud_bill.cancel_bill(db, db_obj=bill)
    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="DELETE",
        table_name="bills",
        record_id=bill_id,
        description=f"Huỷ hóa đơn {bill.bill_number}",
    )
    await db.commit()
    return cancelled
