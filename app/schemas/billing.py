"""
Pydantic schemas cho viện phí và thanh toán.

Schemas::

    BillCreate / BillUpdate / BillResponse / BillSummary
    PaymentCreate / PaymentResponse
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.enums import BillStatus, PaymentMethod, PaymentType


# ─── BillItem ────────────────────────────────────────────────────────────────

class BillItemResponse(BaseModel):
    id:                   int
    bill_id:              int
    prescription_item_id: Optional[int] = None
    item_type:            str
    item_code:            Optional[str] = None
    item_name:            str
    unit:                 Optional[str] = None
    quantity:             Decimal
    unit_price:           Optional[Decimal] = None
    payment_type:         PaymentType
    total_amount:         Optional[Decimal] = None
    bhyt_amount:          Optional[Decimal] = None
    patient_amount:       Optional[Decimal] = None
    sort_order:           int = 0
    model_config = {"from_attributes": True}


# ─── Payment ─────────────────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    payment_method:  PaymentMethod = PaymentMethod.CASH
    amount:          Decimal       = Field(..., gt=0, description="Số tiền thanh toán")
    transaction_ref: Optional[str] = Field(None, max_length=100)
    note:            Optional[str] = None
    is_deposit:      bool          = False
    is_refund:       bool          = False


class PaymentResponse(BaseModel):
    id:              int
    bill_id:         int
    cashier_id:      Optional[int] = None
    payment_method:  PaymentMethod
    amount:          Decimal
    paid_at:         datetime
    transaction_ref: Optional[str] = None
    note:            Optional[str] = None
    is_deposit:      bool
    is_refund:       bool
    created_at:      datetime
    model_config = {"from_attributes": True}


# ─── Bill ────────────────────────────────────────────────────────────────────

class BillCreate(BaseModel):
    """
    Thu ngân tạo bill từ một phiếu khám đã COMPLETED.
    Các BillItem được sinh tự động từ PrescriptionItems.
    """
    examination_id: int
    deposit_amount: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    note: Optional[str] = None


class BillUpdate(BaseModel):
    discount_amount: Optional[Decimal] = None
    deposit_amount:  Optional[Decimal] = None
    note:            Optional[str]     = None
    bhyt_approved_code: Optional[str] = Field(None, max_length=50)


class BillResponse(BaseModel):
    id:              int
    bill_number:     str
    examination_id:  Optional[int]  = None
    patient_id:      Optional[int]  = None
    reception_id:    Optional[int]  = None
    status:          BillStatus
    issued_at:       Optional[datetime] = None
    paid_at:         Optional[datetime] = None
    cashier_id:      Optional[int]  = None
    cashier_name:    Optional[str]  = None
    drug_total:      Decimal
    cls_total:       Decimal
    service_total:   Decimal
    grand_total:     Decimal
    bhyt_pays:       Decimal
    patient_pays:    Decimal
    discount_amount: Decimal
    deposit_amount:  Decimal
    balance_due:     Decimal
    insurance_number:    Optional[str] = None
    bhyt_contract_no:    Optional[str] = None
    bhyt_approved_code:  Optional[str] = None
    note:            Optional[str]  = None
    items:           List[BillItemResponse] = []
    payments:        List[PaymentResponse]  = []
    created_at:      datetime
    updated_at:      datetime
    model_config = {"from_attributes": True}


class BillSummary(BaseModel):
    """Tóm tắt bill cho danh sách."""
    id:           int
    bill_number:  str
    patient_id:   Optional[int] = None
    status:       BillStatus
    grand_total:  Decimal
    balance_due:  Decimal
    issued_at:    Optional[datetime] = None
    paid_at:      Optional[datetime] = None
    created_at:   datetime
    model_config = {"from_attributes": True}
