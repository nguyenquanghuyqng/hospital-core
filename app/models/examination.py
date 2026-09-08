"""
ORM models cho phiếu khám bệnh và các thực thể con.

Quan hệ::

    Reception  1 ──── 1  Examination
    Examination 1 ──── N  Diagnosis
    Examination 1 ──── N  PrescriptionItem

Luồng trạng thái của Examination::

    DRAFT → SAVED → COMPLETED
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
    """
    Bảng ``examinations`` — phiếu khám bệnh, liên kết 1-1 với Reception.

    Chứa toàn bộ nội dung lâm sàng của một lượt khám: thông tin bảo hiểm,
    triệu chứng lâm sàng, chẩn đoán, hướng xử trí, và kết quả khám.

    Attributes:
        id: Khoá chính tự tăng.
        reception_id: FK unique tới ``receptions`` (1-1, CASCADE delete).
        patient_id: FK tới ``patients`` (CASCADE delete).
        doctor_id: FK tới ``users`` — bác sĩ khám (SET NULL khi xoá user).
        status: Trạng thái phiếu khám — xem :class:`~app.models.enums.ExaminationStatus`.
        exam_date: Ngày khám (mặc định hôm nay).
        exam_start_at: Thời điểm bắt đầu khám (ghi tự động khi tạo phiếu).
        exam_end_at: Thời điểm kết thúc khám (ghi tự động khi COMPLETED).
        disposition: Hướng xử trí sau khám — xem :class:`~app.models.enums.DispositionType`.
        admit_priority: Ưu tiên nhập viện nhanh.
        diagnoses: Danh sách chẩn đoán ICD-10 (ordered by sort_order).
        prescription_items: Danh sách kê đơn / chỉ định CLS (ordered by sort_order).
    """

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

    # ── Thông tin vào ─────────────────────────────────────────────────────────
    exam_date     = Column(Date, nullable=False, server_default=func.current_date(), comment="Ngày khám")
    exam_start_at = Column(DateTime(timezone=True), nullable=True, comment="Giờ bắt đầu khám")
    exam_end_at   = Column(DateTime(timezone=True), nullable=True, comment="Giờ kết thúc khám")
    exam_end_date = Column(Date, nullable=True, comment="Ngày kết thúc khám")

    # Đối tượng thanh toán
    subject_type         = Column(String(10),  nullable=True, comment="Mã đối tượng (1=BHYT, 2=DV...)")
    subject_name         = Column(String(100), nullable=True, comment="Tên đối tượng")
    insurance_number     = Column(String(20),  nullable=True, comment="Số thẻ BHYT")
    insurance_valid_from = Column(Date,        nullable=True, comment="Từ ngày BHYT")
    insurance_valid_to   = Column(Date,        nullable=True, comment="Đến ngày BHYT")

    # Chuyển đến / nhận từ
    referral_from_type = Column(String(100), nullable=True, comment="Loại đơn vị giới thiệu")
    referral_from_name = Column(String(200), nullable=True, comment="Tên đơn vị giới thiệu")
    referral_diagnosis = Column(Text,        nullable=True, comment="CĐ nơi giới thiệu")

    # Lâm sàng
    clinical_symptoms = Column(Text, nullable=True, comment="Triệu chứng lâm sàng")

    # ── Thông tin khám ────────────────────────────────────────────────────────
    doctor_name = Column(String(100), nullable=True, comment="Bác sĩ điều trị")
    nurse_name  = Column(String(100), nullable=True, comment="Điều dưỡng phụ trách")

    # Biến chứng
    complications = Column(Text, nullable=True, comment="Biến chứng")

    # Hướng xử trí (loại trừ lẫn nhau)
    disposition = Column(disposition_type_col, nullable=True, comment="Hướng xử trí")

    # Tái khám
    revisit_days   = Column(Integer,    nullable=True, comment="Số ngày hẹn tái khám")
    revisit_result = Column(String(50), nullable=True, comment="Kết quả điều trị (đỡ/khỏi...)")

    # Chuyển tuyến
    transfer_to_facility = Column(String(200), nullable=True, comment="Nơi chuyển tuyến")
    transfer_reason      = Column(Text,        nullable=True, comment="Lý do chuyển tuyến")

    # Nhập viện
    admit_ward    = Column(String(100), nullable=True,  comment="Vào khoa/phòng")
    admit_priority = Column(Boolean, default=False, nullable=False, server_default="false",
                             comment="Ưu tiên nhập viện")

    # Checkbox nhanh
    is_near_poor  = Column(Boolean, default=False, nullable=False, server_default="false")
    is_poor       = Column(Boolean, default=False, nullable=False, server_default="false")
    flag_priority = Column(Boolean, default=False, nullable=False, server_default="false",
                           comment="Ưu tiên")

    # ── Quan hệ ───────────────────────────────────────────────────────────────
    reception          = relationship("Reception",         foreign_keys=[reception_id], lazy="select")
    patient            = relationship("Patient",           foreign_keys=[patient_id],   lazy="select")
    doctor             = relationship("User",              foreign_keys=[doctor_id],    lazy="select")
    diagnoses          = relationship("Diagnosis",         back_populates="examination",
                                      cascade="all, delete-orphan", order_by="Diagnosis.sort_order")
    prescription_items = relationship("PrescriptionItem",  back_populates="examination",
                                      cascade="all, delete-orphan", order_by="PrescriptionItem.sort_order")

    def __repr__(self) -> str:
        """Trả về chuỗi đại diện ngắn gọn cho debugging."""
        return f"<Examination id={self.id} reception={self.reception_id} status={self.status}>"


class Diagnosis(Base, TimestampMixin):
    """
    Bảng ``diagnoses`` — chẩn đoán ICD-10 của một phiếu khám.

    Một phiếu khám có thể có nhiều chẩn đoán.
    Đúng một chẩn đoán được đánh dấu ``is_primary=True`` là chẩn đoán chính;
    các dòng còn lại là chẩn đoán kèm theo.

    Attributes:
        id: Khoá chính tự tăng.
        examination_id: FK tới ``examinations`` (CASCADE delete).
        icd_code: Mã bệnh theo ICD-10 (tuỳ chọn, VD: ``J18.9``).
        icd_name: Tên bệnh / chẩn đoán bằng tiếng Việt (bắt buộc).
        is_primary: ``True`` = chẩn đoán chính, ``False`` = chẩn đoán kèm theo.
        note: Ghi chú bổ sung.
        sort_order: Thứ tự hiển thị trong phiếu khám.
    """

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
        """Trả về chuỗi đại diện ngắn gọn cho debugging."""
        return f"<Diagnosis {self.icd_code} {self.icd_name[:30]}>"


class PrescriptionItem(Base, TimestampMixin):
    """
    Bảng ``prescription_items`` — một dòng kê đơn thuốc hoặc chỉ định CLS.

    Phân biệt bởi ``item_type``:
    - ``drug`` : thuốc kê đơn (có hướng dẫn sử dụng, ngày hiệu lực).
    - ``cls``  : chỉ định cận lâm sàng (xét nghiệm, chụp chiếu…).

    Chi phí được tính tự động nếu có ``unit_price`` và ``quantity``.
    Phân bổ BHYT / bệnh nhân cùng chi trả được lưu trong ``bhyt_amount``
    và ``patient_amount``.

    Attributes:
        id: Khoá chính tự tăng.
        examination_id: FK tới ``examinations`` (CASCADE delete).
        item_type: ``"drug"`` hoặc ``"cls"``.
        item_code: Mã thuốc / dịch vụ trong danh mục (tuỳ chọn).
        item_name: Tên thuốc / dịch vụ CLS (bắt buộc).
        unit: Đơn vị tính (viên, ống, lần…).
        quantity: Số lượng (> 0).
        unit_price: Đơn giá.
        usage_instruction: Cách dùng dành cho thuốc (sáng 1v, tối 1v…).
        valid_from / valid_to: Thời gian hiệu lực đơn thuốc.
        payment_type: Loại chi trả — xem :class:`~app.models.enums.PaymentType`.
        total_amount: Thành tiền (tự tính = quantity × unit_price nếu để trống).
        bhyt_amount: Số tiền BHYT chi trả.
        patient_amount: Số tiền bệnh nhân cùng chi trả (CCT).
        sort_order: Thứ tự hiển thị trong phiếu.
    """

    __tablename__ = "prescription_items"

    id             = Column(Integer, primary_key=True, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id", ondelete="CASCADE"),
                            nullable=False, index=True)

    # Phân loại
    item_type = Column(String(10), nullable=False, server_default="drug",
                       comment="drug = thuốc | cls = cận lâm sàng")

    # Thông tin thuốc / dịch vụ
    item_code = Column(String(50),  nullable=True,  comment="Mã thuốc/dịch vụ")
    item_name = Column(String(300), nullable=False,  comment="Tên thuốc/dịch vụ CLS")
    unit      = Column(String(30),  nullable=True,   comment="Đơn vị (viên, ống, lần...)")
    quantity  = Column(Numeric(10, 2), nullable=False, server_default="1", comment="Số lượng")
    unit_price = Column(Numeric(15, 2), nullable=True, comment="Đơn giá")

    # Hướng dẫn (dành cho thuốc)
    usage_instruction = Column(Text, nullable=True, comment="Cách dùng (sáng 1v, tối 1v...)")
    valid_from        = Column(Date, nullable=True, comment="Từ ngày hiệu lực đơn thuốc")
    valid_to          = Column(Date, nullable=True, comment="Đến ngày hiệu lực đơn thuốc")

    # Loại chi trả
    payment_type = Column(
        payment_type_col,
        nullable=False,
        default=PaymentType.BHYT,
        server_default=PaymentType.BHYT.value,
    )

    # Chi phí tính toán
    total_amount   = Column(Numeric(15, 2), nullable=True, comment="Thành tiền")
    bhyt_amount    = Column(Numeric(15, 2), nullable=True, comment="BHYT chi trả")
    patient_amount = Column(Numeric(15, 2), nullable=True, comment="Bệnh nhân cùng chi trả (CCT)")

    # Metadata
    room_name   = Column(String(50),  nullable=True,  comment="Phòng khám kê")
    doctor_name = Column(String(100), nullable=True,  comment="Bác sĩ kê")
    sort_order  = Column(Integer, default=0, nullable=False, server_default="0")

    examination = relationship("Examination", back_populates="prescription_items")

    def __repr__(self) -> str:
        """Trả về chuỗi đại diện ngắn gọn cho debugging."""
        return f"<PrescriptionItem {self.item_type} {self.item_name[:30]}>"
