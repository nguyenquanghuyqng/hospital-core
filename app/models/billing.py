"""
ORM models cho viện phí và thanh toán.

Quan hệ::

    Examination 1 ──── 1  Bill
    Bill 1 ──── N  BillItem
    Bill 1 ──── N  Payment

Luồng::

    Bác sĩ complete_examination
    → Thu ngân tạo Bill(DRAFT) từ PrescriptionItems
    → Bill(ISSUED) phát hành
    → Bệnh nhân nộp tiền → Payment ghi nhận
    → Bill(PAID) khi đủ số tiền
"""
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, DateTime, Text,
    Boolean, ForeignKey, Numeric, func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.base_model import TimestampMixin
from app.models.enums import (
    BillStatus, bill_status_type,
    PaymentMethod, payment_method_type,
    PaymentType, payment_type_col,
)


class Bill(Base, TimestampMixin):
    """
    Bảng ``bills`` — hóa đơn viện phí cho một lượt khám.

    Mỗi ``Examination`` có tối đa một ``Bill``.
    Tổng tiền được tính từ các ``BillItem`` bên dưới.

    Attributes:
        bill_number: Số hóa đơn (tự sinh, dạng HD2026XXXXXX).
        examination_id: FK 1-1 tới ``examinations``.
        patient_id: FK tới ``patients`` (denormalized).
        reception_id: FK tới ``receptions`` (denormalized).
        status: Trạng thái hóa đơn.
        issued_at: Thời điểm phát hành hóa đơn.
        paid_at: Thời điểm thanh toán xong.
        cashier_id: FK tới ``users`` — thu ngân.
        cashier_name: Tên thu ngân (snapshot).
        drug_total: Tổng tiền thuốc.
        cls_total: Tổng tiền CLS.
        service_total: Tổng tiền dịch vụ khác.
        grand_total: Tổng cộng.
        bhyt_pays: BHYT chi trả.
        patient_pays: Bệnh nhân cùng chi trả.
        discount_amount: Giảm giá.
        deposit_amount: Tạm ứng đã nộp.
        balance_due: Số tiền còn lại phải nộp.
        note: Ghi chú.
    """

    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)

    bill_number    = Column(String(30), unique=True, index=True, nullable=False,
                            comment="Số hóa đơn HD2026XXXXXX")
    examination_id = Column(Integer, ForeignKey("examinations.id", ondelete="SET NULL"),
                            nullable=True, unique=True, index=True)
    patient_id     = Column(Integer, ForeignKey("patients.id", ondelete="SET NULL"),
                            nullable=True, index=True)
    reception_id   = Column(Integer, ForeignKey("receptions.id", ondelete="SET NULL"),
                            nullable=True, index=True)

    # ── Trạng thái ────────────────────────────────────────────────────────────
    status = Column(
        bill_status_type,
        nullable=False,
        default=BillStatus.DRAFT,
        server_default=BillStatus.DRAFT.value,
    )
    issued_at  = Column(DateTime(timezone=True), nullable=True, comment="Giờ phát hành")
    paid_at    = Column(DateTime(timezone=True), nullable=True, comment="Giờ thanh toán xong")

    # ── Thu ngân ──────────────────────────────────────────────────────────────
    cashier_id   = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cashier_name = Column(String(100), nullable=True, comment="Tên thu ngân (snapshot)")

    # ── Tổng tiền (tính từ BillItem) ──────────────────────────────────────────
    drug_total    = Column(Numeric(15, 2), nullable=False, server_default="0", comment="Tiền thuốc")
    cls_total     = Column(Numeric(15, 2), nullable=False, server_default="0", comment="Tiền CLS")
    service_total = Column(Numeric(15, 2), nullable=False, server_default="0", comment="Tiền DV khác")
    grand_total   = Column(Numeric(15, 2), nullable=False, server_default="0", comment="Tổng cộng")
    bhyt_pays     = Column(Numeric(15, 2), nullable=False, server_default="0", comment="BHYT chi trả")
    patient_pays  = Column(Numeric(15, 2), nullable=False, server_default="0", comment="BN cùng chi trả")
    discount_amount = Column(Numeric(15, 2), nullable=False, server_default="0", comment="Giảm giá")
    deposit_amount  = Column(Numeric(15, 2), nullable=False, server_default="0", comment="Tạm ứng")
    balance_due     = Column(Numeric(15, 2), nullable=False, server_default="0",
                             comment="Còn phải nộp = patient_pays - deposit_amount - discount_amount")

    # ── Bảo hiểm ──────────────────────────────────────────────────────────────
    insurance_number   = Column(String(20), nullable=True, comment="Số thẻ BHYT")
    bhyt_contract_no   = Column(String(50), nullable=True, comment="Số HĐ BHYT")
    bhyt_approved_code = Column(String(50), nullable=True, comment="Mã duyệt BHYT")

    note = Column(Text, nullable=True)

    # ── Quan hệ ───────────────────────────────────────────────────────────────
    items    = relationship("BillItem",  back_populates="bill",
                            cascade="all, delete-orphan", order_by="BillItem.sort_order")
    payments = relationship("Payment",   back_populates="bill",
                            cascade="all, delete-orphan", order_by="Payment.paid_at")
    cashier  = relationship("User",      foreign_keys=[cashier_id], lazy="select")

    def __repr__(self) -> str:
        return f"<Bill {self.bill_number} status={self.status} total={self.grand_total}>"


class BillItem(Base):
    """
    Bảng ``bill_items`` — từng dòng chi phí trong hóa đơn.

    Được sinh từ ``PrescriptionItem`` khi thu ngân phát hành bill.
    Lưu giữ snapshot giá tại thời điểm phát hành (giá có thể thay đổi sau).

    Attributes:
        bill_id: FK tới ``bills``.
        prescription_item_id: FK tới ``prescription_items`` (nếu có).
        item_type: drug | cls | service.
        item_code: Mã thuốc/dịch vụ.
        item_name: Tên (snapshot).
        unit: Đơn vị.
        quantity: Số lượng.
        unit_price: Đơn giá tại thời điểm phát hành.
        payment_type: Loại chi trả.
        total_amount: Thành tiền.
        bhyt_amount: BHYT chi trả.
        patient_amount: BN cùng chi trả.
    """

    __tablename__ = "bill_items"

    id                   = Column(Integer, primary_key=True, index=True)
    bill_id              = Column(Integer, ForeignKey("bills.id", ondelete="CASCADE"),
                                  nullable=False, index=True)
    prescription_item_id = Column(Integer, ForeignKey("prescription_items.id", ondelete="SET NULL"),
                                  nullable=True)

    item_type  = Column(String(10),  nullable=False, server_default="drug")
    item_code  = Column(String(50),  nullable=True)
    item_name  = Column(String(300), nullable=False)
    unit       = Column(String(30),  nullable=True)
    quantity   = Column(Numeric(10, 2), nullable=False, server_default="1")
    unit_price = Column(Numeric(15, 2), nullable=True)
    payment_type = Column(payment_type_col, nullable=False,
                          default=PaymentType.BHYT, server_default=PaymentType.BHYT.value)
    total_amount   = Column(Numeric(15, 2), nullable=True)
    bhyt_amount    = Column(Numeric(15, 2), nullable=True)
    patient_amount = Column(Numeric(15, 2), nullable=True)
    sort_order     = Column(Integer, nullable=False, default=0, server_default="0")

    bill = relationship("Bill", back_populates="items")

    def __repr__(self) -> str:
        return f"<BillItem {self.item_name} qty={self.quantity} total={self.total_amount}>"


class Payment(Base, TimestampMixin):
    """
    Bảng ``payments`` — một lần thanh toán cho hóa đơn.

    Một hóa đơn có thể có nhiều lần thanh toán (tạm ứng, thanh toán bổ sung...).

    Attributes:
        bill_id: FK tới ``bills``.
        payment_method: Phương thức thanh toán.
        amount: Số tiền thanh toán.
        paid_at: Thời điểm thanh toán.
        cashier_id: Thu ngân ghi nhận.
        transaction_ref: Mã giao dịch (ngân hàng, ví điện tử).
        note: Ghi chú.
        is_deposit: Đây là khoản tạm ứng (chưa phải thanh toán cuối).
        is_refund: Đây là khoản hoàn tiền.
    """

    __tablename__ = "payments"

    id         = Column(Integer, primary_key=True, index=True)
    bill_id    = Column(Integer, ForeignKey("bills.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    cashier_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    payment_method  = Column(payment_method_type, nullable=False,
                             default=PaymentMethod.CASH, server_default=PaymentMethod.CASH.value)
    amount          = Column(Numeric(15, 2), nullable=False, comment="Số tiền")
    paid_at         = Column(DateTime(timezone=True), nullable=False,
                             server_default=func.now(), comment="Thời điểm thanh toán")
    transaction_ref = Column(String(100), nullable=True, comment="Mã giao dịch")
    note            = Column(Text, nullable=True)
    is_deposit      = Column(Boolean, nullable=False, default=False, server_default="false",
                             comment="Tạm ứng trước khi có bill")
    is_refund       = Column(Boolean, nullable=False, default=False, server_default="false",
                             comment="Hoàn tiền")

    bill    = relationship("Bill",  back_populates="payments")
    cashier = relationship("User",  foreign_keys=[cashier_id], lazy="select")

    def __repr__(self) -> str:
        return f"<Payment {self.amount} via {self.payment_method} at {self.paid_at}>"
