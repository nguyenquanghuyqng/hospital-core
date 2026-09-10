"""
ORM model cho đơn thuốc điện tử chuẩn Bộ Y tế (donthuocquocgia.vn).

Quan hệ::

    Examination  1 ──── 1  Prescription
    Prescription 1 ──── N  PrescriptionItem  (via prescription_items.prescription_id)

Luồng vòng đời đơn::

    Kê đơn → DRAFT phiếu khám
    Hoàn tất khám (COMPLETED) → Prescription được tạo tự động → push_status = PENDING
    Background task → push lên BYT → SUCCESS hoặc ERROR
    ERROR → retry tối đa 5 lần → nếu vẫn lỗi cần admin xử lý thủ công

Mã đơn 14 ký tự (XXXXXYYYYYYY-Z):
    XXXXX   = 5 ký tự mã cơ sở (facility_code từ system_config)
    YYYYYYY = 7 ký tự ngẫu nhiên (unique per facility, unique constraint DB)
    Z       = N (gây nghiện) / H (hướng thần-tiền chất) / C (đơn khác)
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Text,
    Boolean, ForeignKey, Numeric, SmallInteger, func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.base_model import TimestampMixin
from app.models.enums import (
    PrescriptionType,    prescription_type_col,
    PrescriptionPushStatus, prescription_push_status_col,
)


class Prescription(Base, TimestampMixin):
    """
    Bảng ``prescriptions`` — đơn thuốc điện tử chính thức theo chuẩn BYT.

    Mỗi phiếu khám (:class:`~app.models.examination.Examination`) tạo ra
    đúng **một** đơn thuốc. Đơn được tạo tự động khi bác sĩ hoàn tất phiếu khám.

    Attributes:
        id: Khoá chính tự tăng.
        examination_id: FK 1-1 → ``examinations`` (CASCADE delete).
        patient_id: FK → ``patients`` (CASCADE delete).
        doctor_id: FK → ``users`` (SET NULL khi xoá user).
        prescription_code: Mã đơn 14 ký tự XXXXXYYYYYYY-Z (UNIQUE toàn bảng).
        facility_code: Snapshot 5 ký tự mã cơ sở tại thời điểm tạo.
        prescription_type: N / H / C — xác định tự động từ danh mục thuốc kê.
        push_status: Trạng thái đẩy lên hệ thống quốc gia.
        is_inpatient: True = Nội trú (không push real-time), False = Ngoại trú.
        treatment_from/to: Đợt dùng thuốc — bắt buộc với đơn N và H.
        patient_phone: SĐT bắt buộc trên mọi đơn (snapshot từ patients.phone).
        patient_weight_kg: Cân nặng — bắt buộc nếu BN < 72 tháng tuổi.
        patient_gender_code: 1=Nam / 2=Nữ / 3=Khác (chuẩn mã BYT).
        guardian_name: Tên bố/mẹ/người đưa trẻ — bắt buộc BN < 72 tháng tuổi.
        recipient_cccd: CCCD/CMND người nhận thuốc — bắt buộc với đơn N/H.
        recipient_name: Họ tên người nhận thuốc N/H.
        national_ref_id: ID đơn trả về từ hệ thống quốc gia BYT.
        retry_count: Số lần đã retry (tối đa 5).
        retry_at: Thời điểm dự kiến retry tiếp theo.
        error_log: JSON log lỗi từ API BYT.
        doctor_name: Snapshot tên bác sĩ.
        doctor_national_code: Snapshot mã liên thông bác sĩ.
        sent_at: Thời điểm gửi thành công.
        sold_at: Thời điểm nhà thuốc xác nhận đã bán (đồng bộ từ BYT).
    """

    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)

    # ── Liên kết ──────────────────────────────────────────────────────────────
    examination_id = Column(
        Integer, ForeignKey("examinations.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    patient_id = Column(
        Integer, ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    doctor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    # ── Mã đơn 14 ký tự ───────────────────────────────────────────────────────
    prescription_code = Column(
        String(16), nullable=True, unique=True,
        comment="Mã đơn 14 ký tự: XXXXXYYYYYYY-Z",
    )
    facility_code = Column(
        String(5), nullable=True,
        comment="5 ký tự mã cơ sở (snapshot tại thời điểm tạo đơn)",
    )

    # ── Phân loại và trạng thái ───────────────────────────────────────────────
    prescription_type = Column(
        prescription_type_col,
        nullable=False,
        default=PrescriptionType.C,
        server_default=PrescriptionType.C.value,
        comment="N=gây nghiện | H=hướng thần | C=thường",
    )
    push_status = Column(
        prescription_push_status_col,
        nullable=False,
        default=PrescriptionPushStatus.PENDING,
        server_default=PrescriptionPushStatus.PENDING.value,
        comment="Trạng thái đẩy lên hệ thống quốc gia",
    )

    # ── Hình thức điều trị ────────────────────────────────────────────────────
    is_inpatient = Column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="True=Nội trú (báo cáo batch), False=Ngoại trú (push real-time)",
    )

    # ── Đợt dùng thuốc (bắt buộc với N/H) ────────────────────────────────────
    treatment_from = Column(Date, nullable=True, comment="Đợt dùng thuốc từ ngày")
    treatment_to   = Column(Date, nullable=True, comment="Đợt dùng thuốc đến ngày")

    # ── Thông tin BN snapshot tại thời điểm kê ────────────────────────────────
    patient_phone      = Column(String(20),     nullable=True,  comment="SĐT bắt buộc trên mọi đơn")
    patient_weight_kg  = Column(Numeric(5, 1),  nullable=True,  comment="Cân nặng (bắt buộc BN < 72 tháng)")
    patient_gender_code = Column(SmallInteger,  nullable=True,  comment="1=Nam 2=Nữ 3=Khác (chuẩn BYT)")
    guardian_name      = Column(String(100),    nullable=True,  comment="Tên bố/mẹ/người đưa trẻ (bắt buộc BN < 72 tháng)")

    # ── Người nhận (bắt buộc với đơn N/H) ────────────────────────────────────
    recipient_cccd = Column(String(12),  nullable=True, comment="CCCD/CMND người nhận thuốc N/H")
    recipient_name = Column(String(100), nullable=True, comment="Họ tên người nhận thuốc N/H")

    # ── Ref từ hệ thống quốc gia ──────────────────────────────────────────────
    national_ref_id = Column(String(100), nullable=True, comment="ID đơn trên hệ thống BYT")
    sent_at         = Column(DateTime(timezone=True), nullable=True, comment="Thời điểm gửi thành công")
    sold_at         = Column(DateTime(timezone=True), nullable=True, comment="Thời điểm nhà thuốc xác nhận đã bán")

    # ── Retry và log lỗi ──────────────────────────────────────────────────────
    retry_count = Column(Integer, nullable=False, default=0, server_default="0")
    retry_at    = Column(DateTime(timezone=True), nullable=True, comment="Thời điểm retry tiếp theo")
    error_log   = Column(Text, nullable=True, comment="JSON log lỗi từ API BYT")

    # ── Snapshot bác sĩ ───────────────────────────────────────────────────────
    doctor_name          = Column(String(100), nullable=True)
    doctor_national_code = Column(String(20),  nullable=True, comment="Snapshot mã liên thông BS")

    # ── Quan hệ ───────────────────────────────────────────────────────────────
    examination        = relationship("Examination",        foreign_keys=[examination_id], lazy="select")
    patient            = relationship("Patient",            foreign_keys=[patient_id],    lazy="select")
    doctor             = relationship("User",               foreign_keys=[doctor_id],     lazy="select")
    prescription_items = relationship(
        "PrescriptionItem",
        primaryjoin="Prescription.id == foreign(PrescriptionItem.prescription_id)",
        lazy="select",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Prescription id={self.id} code={self.prescription_code!r} "
            f"type={self.prescription_type} status={self.push_status}>"
        )
