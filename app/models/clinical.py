"""
ORM models cho kết quả CLS (cận lâm sàng).

Quan hệ::

    PrescriptionItem (item_type='cls') 1 ──── 1  ClsResult
    ClsResult 1 ──── N  ClsResultValue

Luồng::

    PrescriptionItem (cls) được tạo → ClsResult(PENDING) sinh kèm
    → Kỹ thuật viên điền kết quả → ClsResult(COMPLETED)
    → Bác sĩ đọc kết quả → VisitStatus chuyển CLS_RESULT
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Text,
    Boolean, ForeignKey, Numeric, func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.base_model import TimestampMixin
from app.models.enums import ClsResultStatus, cls_result_status_type


class ClsResult(Base, TimestampMixin):
    """
    Bảng ``cls_results`` — phiếu kết quả cận lâm sàng.

    Mỗi dòng ``PrescriptionItem`` có ``item_type='cls'`` sẽ có đúng một
    ``ClsResult`` tương ứng. Kết quả chi tiết theo từng chỉ số được lưu
    trong :class:`ClsResultValue`.

    Attributes:
        prescription_item_id: FK 1-1 tới ``prescription_items``.
        examination_id: FK tới ``examinations`` (denormalized để query nhanh).
        patient_id: FK tới ``patients`` (denormalized).
        service_code: Mã dịch vụ CLS (snapshot).
        service_name: Tên dịch vụ CLS (snapshot).
        status: Trạng thái kết quả (PENDING → IN_PROCESS → COMPLETED).
        performed_at: Thời điểm thực hiện xét nghiệm.
        result_at: Thời điểm có kết quả.
        performed_by: Tên kỹ thuật viên thực hiện.
        result_summary: Tóm tắt kết quả dạng text (in phiếu).
        result_note: Ghi chú / nhận xét của kỹ thuật viên.
        result_file_url: Đường dẫn file đính kèm (PDF, hình ảnh).
        is_abnormal: Có chỉ số bất thường nào không.
        values: Danh sách chỉ số kết quả chi tiết.
    """

    __tablename__ = "cls_results"

    id = Column(Integer, primary_key=True, index=True)

    # ── Liên kết ──────────────────────────────────────────────────────────────
    prescription_item_id = Column(
        Integer,
        ForeignKey("prescription_items.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
        comment="FK 1-1 tới prescription_items",
    )
    examination_id = Column(
        Integer,
        ForeignKey("examinations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    patient_id = Column(
        Integer,
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # ── Thông tin dịch vụ (snapshot) ─────────────────────────────────────────
    service_code = Column(String(30),  nullable=True,  comment="Mã DV CLS")
    service_name = Column(String(300), nullable=False, comment="Tên DV CLS")
    department   = Column(String(100), nullable=True,  comment="Khoa/phòng thực hiện")

    # ── Trạng thái ────────────────────────────────────────────────────────────
    status = Column(
        cls_result_status_type,
        nullable=False,
        default=ClsResultStatus.PENDING,
        server_default=ClsResultStatus.PENDING.value,
    )

    # ── Thực hiện ─────────────────────────────────────────────────────────────
    performed_at = Column(DateTime(timezone=True), nullable=True, comment="Giờ thực hiện")
    result_at    = Column(DateTime(timezone=True), nullable=True, comment="Giờ có kết quả")
    performed_by = Column(String(100), nullable=True, comment="KTV thực hiện")
    verified_by  = Column(String(100), nullable=True, comment="BS/KTV duyệt kết quả")

    # ── Kết quả ───────────────────────────────────────────────────────────────
    result_summary  = Column(Text,        nullable=True, comment="Tóm tắt kết quả (in phiếu)")
    result_note     = Column(Text,        nullable=True, comment="Nhận xét / ghi chú KTV")
    result_file_url = Column(String(500), nullable=True, comment="URL file đính kèm (PDF/ảnh)")
    is_abnormal     = Column(Boolean, nullable=False, default=False, server_default="false",
                             comment="Có chỉ số bất thường")

    # ── Quan hệ ───────────────────────────────────────────────────────────────
    prescription_item = relationship(
        "PrescriptionItem",
        foreign_keys=[prescription_item_id],
        lazy="select",
    )
    values = relationship(
        "ClsResultValue",
        back_populates="cls_result",
        cascade="all, delete-orphan",
        order_by="ClsResultValue.sort_order",
    )

    def __repr__(self) -> str:
        return f"<ClsResult id={self.id} service={self.service_name} status={self.status}>"


class ClsResultValue(Base):
    """
    Bảng ``cls_result_values`` — từng chỉ số kết quả của một phiếu CLS.

    Ví dụ: HGB = 120 g/dL (ref: 120–160), WBC = 8.5 10³/μL (ref: 4–10).

    Attributes:
        cls_result_id: FK tới ``cls_results``.
        indicator_name: Tên chỉ số (VD: HGB, WBC).
        indicator_code: Mã chỉ số (tuỳ chọn).
        value_text: Giá trị dạng text (cho kết quả không phải số, VD: "Dương tính").
        value_numeric: Giá trị số.
        unit: Đơn vị đo (g/dL, 10³/μL...).
        ref_min: Giá trị tham chiếu thấp nhất.
        ref_max: Giá trị tham chiếu cao nhất.
        ref_text: Khoảng tham chiếu dạng text (VD: "120 - 160").
        is_abnormal: Chỉ số này có nằm ngoài khoảng tham chiếu không.
        sort_order: Thứ tự hiển thị.
    """

    __tablename__ = "cls_result_values"

    id            = Column(Integer, primary_key=True, index=True)
    cls_result_id = Column(
        Integer,
        ForeignKey("cls_results.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    indicator_name = Column(String(100), nullable=False, comment="Tên chỉ số (VD: HGB)")
    indicator_code = Column(String(50),  nullable=True,  comment="Mã chỉ số")
    value_text     = Column(String(200), nullable=True,  comment="Giá trị text")
    value_numeric  = Column(Numeric(15, 4), nullable=True, comment="Giá trị số")
    unit           = Column(String(50),  nullable=True,  comment="Đơn vị đo")
    ref_min        = Column(Numeric(15, 4), nullable=True, comment="Ngưỡng tham chiếu thấp")
    ref_max        = Column(Numeric(15, 4), nullable=True, comment="Ngưỡng tham chiếu cao")
    ref_text       = Column(String(100), nullable=True,  comment="Khoảng tham chiếu text")
    is_abnormal    = Column(Boolean, nullable=False, default=False, server_default="false")
    sort_order     = Column(Integer, nullable=False, default=0, server_default="0")

    cls_result = relationship("ClsResult", back_populates="values")

    def __repr__(self) -> str:
        return f"<ClsResultValue {self.indicator_name}={self.value_numeric}{self.unit}>"
