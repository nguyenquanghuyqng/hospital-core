"""
Model phiếu khám bệnh.

Quan hệ:
  Reception 1 ── 1 Examination
  Examination 1 ── N Diagnosis
  Examination 1 ── N PrescriptionItem
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Text,
    Boolean, ForeignKey, Numeric, func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.base_model import TimestampMixin
from app.models.enums import (
    ExaminationStatus, examination_status_type,
    DispositionType,  disposition_type_col,
    PaymentType,      payment_type_col,
)


class Examination(Base, TimestampMixin):
    """Phiếu khám bệnh — gắn 1-1 với Reception."""
    __tablename__ = "examinations"

    id           = Column(Integer, primary_key=True, index=True)

    # ── Liên kết ──────────────────────────────────────────────────────────────
    reception_id = Column(Integer, ForeignKey("receptions.id", ondelete="CASCADE"),
                          nullable=False, unique=True, index=True)
    patient_id   = Column(Integer, ForeignKey("patients.id",   ondelete="CASCADE"),
                          nullable=False, index=True)
    doctor_id    = Column(Integer, ForeignKey("users.id",      ondelete="SET NULL"),
                          nullable=True, index=True)

    # ── Trạng thái ────────────────────────────────────────────────────────────
    status = Column(
        examination_status_type,
        nullable=False,
        default=ExaminationStatus.DRAFT,
        server_default=ExaminationStatus.DRAFT.value,
    )

    # ── Khung II — Thông tin vào ───────────────────────────────────────────────
    exam_date      = Column(Date, nullable=False, server_default=func.current_date(), comment="Ngày khám")
    exam_start_at  = Column(DateTime(timezone=True), nullable=True,  comment="Giờ bắt đầu khám")
    exam_end_at    = Column(DateTime(timezone=True), nullable=True,  comment="Giờ kết thúc khám")
    exam_end_date  = Column(Date, nullable=True, comment="Ngày kết thúc khám")

    # Đối tượng thanh toán (kế thừa từ Reception nhưng có thể thay đổi)
    subject_type   = Column(String(10),  nullable=True, comment="Mã đối tượng (1=BHYT, 2=DV...)")
    subject_name   = Column(String(100), nullable=True, comment="Tên đối tượng")
    insurance_number     = Column(String(20), nullable=True, comment="Số thẻ BHYT")
    insurance_valid_from = Column(Date,       nullable=True, comment="Từ ngày BHYT")
    insurance_valid_to   = Column(Date,       nullable=True, comment="Đến ngày BHYT")

    # Chuyển đến / nhận từ
    referral_from_type = Column(String(100), nullable=True, comment="Loại đơn vị giới thiệu")
    referral_from_name = Column(String(200), nullable=True, comment="Tên đơn vị giới thiệu")
    referral_diagnosis = Column(Text,        nullable=True, comment="CĐ nơi giới thiệu")

    # Lâm sàng
    clinical_symptoms = Column(Text, nullable=True, comment="Triệu chứng lâm sàng")

    # ── Khung III — Thông tin khám ─────────────────────────────────────────────
    doctor_name = Column(String(100), nullable=True, comment="Bác sĩ điều trị")
    nurse_name  = Column(String(100), nullable=True, comment="Điều dưỡng phụ trách")

    # Biến chứng
    complications = Column(Text, nullable=True, comment="Biến chứng")

    # Hướng xử trí (loại trừ lẫn nhau)
    disposition = Column(
        disposition_type_col,
        nullable=True,
        comment="Hướng xử trí",
    )

    # Tái khám
    revisit_days   = Column(Integer, nullable=True, comment="Số ngày hẹn tái khám")
    revisit_result = Column(String(50), nullable=True, comment="Kết quả điều trị (đỡ/khỏi...)")

    # Chuyển tuyến
    transfer_to_facility = Column(String(200), nullable=True, comment="Nơi chuyển tuyến")
    transfer_reason      = Column(Text,        nullable=True, comment="Lý do chuyển tuyến")

    # Nhập viện
    admit_ward    = Column(String(100), nullable=True, comment="Vào khoa/phòng")
    admit_priority = Column(Boolean, default=False, nullable=False, server_default="false",
                            comment="Ưu tiên nhập viện")

    # Checkbox nhanh
    is_near_poor = Column(Boolean, default=False, nullable=False, server_default="false")
    is_poor      = Column(Boolean, default=False, nullable=False, server_default="false")
    flag_priority = Column(Boolean, default=False, nullable=False, server_default="false",
                           comment="Ưu tiên")

    # ── Quan hệ ───────────────────────────────────────────────────────────────
    reception         = relationship("Reception", foreign_keys=[reception_id], lazy="select")
    patient           = relationship("Patient",   foreign_keys=[patient_id],   lazy="select")
    doctor            = relationship("User",      foreign_keys=[doctor_id],    lazy="select")
    diagnoses         = relationship("Diagnosis", back_populates="examination",
                                     cascade="all, delete-orphan", order_by="Diagnosis.sort_order")
    prescription_items = relationship("PrescriptionItem", back_populates="examination",
                                      cascade="all, delete-orphan", order_by="PrescriptionItem.sort_order")

    def __repr__(self) -> str:
        return f"<Examination id={self.id} reception={self.reception_id} status={self.status}>"


class Diagnosis(Base, TimestampMixin):
    """Chẩn đoán ICD-10 — nhiều dòng trên 1 phiếu khám."""
    __tablename__ = "diagnoses"

    id             = Column(Integer, primary_key=True, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id", ondelete="CASCADE"),
                            nullable=False, index=True)

    icd_code   = Column(String(20),  nullable=True,  comment="Mã ICD-10")
    icd_name   = Column(String(300), nullable=False,  comment="Tên bệnh/chẩn đoán")
    is_primary = Column(Boolean, default=False, nullable=False, server_default="false",
                        comment="Chẩn đoán chính (True) / kèm theo (False)")
    note       = Column(Text, nullable=True, comment="Ghi chú thêm")
    sort_order = Column(Integer, default=0, nullable=False, server_default="0")

    examination = relationship("Examination", back_populates="diagnoses")

    def __repr__(self) -> str:
        return f"<Diagnosis {self.icd_code} {self.icd_name[:30]}>"


class PrescriptionItem(Base, TimestampMixin):
    """Dòng kê đơn/chỉ định CLS — thuốc hoặc dịch vụ cận lâm sàng."""
    __tablename__ = "prescription_items"

    id             = Column(Integer, primary_key=True, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id", ondelete="CASCADE"),
                            nullable=False, index=True)

    # Phân loại
    item_type = Column(String(10), nullable=False, server_default="drug",
                       comment="drug = thuốc | cls = cận lâm sàng")

    # Thông tin thuốc / dịch vụ
    item_code = Column(String(50),  nullable=True, comment="Mã thuốc/dịch vụ")
    item_name = Column(String(300), nullable=False, comment="Tên thuốc/dịch vụ CLS")
    unit      = Column(String(30),  nullable=True,  comment="Đơn vị (viên, ống, lần...)")
    quantity  = Column(Numeric(10, 2), nullable=False, server_default="1", comment="Số lượng")
    unit_price = Column(Numeric(15, 2), nullable=True, comment="Đơn giá")

    # Hướng dẫn (dành cho thuốc)
    usage_instruction = Column(Text, nullable=True, comment="Cách dùng (sáng 1v, tối 1v...)")
    valid_from = Column(Date, nullable=True, comment="Từ ngày hiệu lực đơn thuốc")
    valid_to   = Column(Date, nullable=True, comment="Đến ngày hiệu lực đơn thuốc")

    # Loại chi trả
    payment_type = Column(
        payment_type_col,
        nullable=False,
        default=PaymentType.BHYT,
        server_default=PaymentType.BHYT.value,
    )

    # Chi phí tính toán
    total_amount  = Column(Numeric(15, 2), nullable=True, comment="Thành tiền")
    bhyt_amount   = Column(Numeric(15, 2), nullable=True, comment="BHYT chi trả")
    patient_amount = Column(Numeric(15, 2), nullable=True, comment="Bệnh nhân cùng chi trả (CCT)")

    # Metadata
    room_name  = Column(String(50),  nullable=True, comment="Phòng khám kê")
    doctor_name = Column(String(100), nullable=True, comment="Bác sĩ kê")
    sort_order = Column(Integer, default=0, nullable=False, server_default="0")

    examination = relationship("Examination", back_populates="prescription_items")

    def __repr__(self) -> str:
        return f"<PrescriptionItem {self.item_type} {self.item_name[:30]}>"
