"""
ORM model tiếp đón — lưu đầy đủ thông tin đăng ký khám bệnh theo chuẩn bệnh viện Việt Nam.

Một ``Reception`` đại diện cho một lượt đăng ký khám của bệnh nhân trong một ngày.
Sau khi nhân viên check-in, reception được liên kết với một :class:`QueueTicket`
và sau đó với một :class:`Examination` khi bác sĩ bắt đầu khám.

Luồng trạng thái (``status``)::

    PENDING → CHECKED_IN → COMPLETED
                         ↘ CANCELLED

Luồng xử lý tại phòng khám bác sĩ (``visit_status``)::

    WAITING → CLS → CLS_RESULT → REVISIT → DONE
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    Text, Date, Boolean, func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.base_model import TimestampMixin
from app.models.enums import ReceptionStatus, reception_status_type, VisitStatus, visit_status_type


class Reception(Base, TimestampMixin):
    """
    Bảng ``receptions`` — lượt đăng ký khám bệnh.

    Lưu đầy đủ các thông tin hành chính, bảo hiểm, và lâm sàng cần thiết
    cho một lượt khám bệnh theo quy trình bệnh viện.

    Attributes:
        id: Khoá chính tự tăng.
        visit_date: Ngày đăng ký khám (mặc định hôm nay).
        visit_time: Giờ đăng ký dạng ``HH:MM``.
        clinic_room: Phòng khám được chỉ định.
        visit_number: Số thứ tự khám trong ngày theo phòng (tự sinh).
        status: Trạng thái tiếp đón — xem :class:`~app.models.enums.ReceptionStatus`.
        visit_status: Trạng thái xử lý tại phòng khám — xem :class:`~app.models.enums.VisitStatus`.
        priority: Độ ưu tiên — ``0`` = bình thường, ``1`` = ưu tiên, ``2`` = cấp cứu.
        patient_id: FK bắt buộc tới ``patients``.
        queue_ticket_id: FK tới ``queue_tickets`` (gán khi check-in, unique 1-1).

    Relationships:
        patient: Bệnh nhân đăng ký khám.
        queue_ticket: Số thứ tự hàng chờ (1-1, tuỳ chọn).
    """

    __tablename__ = "receptions"

    id = Column(Integer, primary_key=True, index=True)

    # ── Ngày giờ đăng ký ──────────────────────────────────────────────
    visit_date = Column(
        Date, nullable=False,
        server_default=func.current_date(),
        comment="Ngày đăng ký",
    )
    visit_time = Column(String(8), nullable=True, comment="Giờ đăng ký (HH:MM)")

    # ── Phòng khám & số khám ──────────────────────────────────────────
    clinic_room  = Column(String(50),  nullable=True, comment="Phòng khám")
    visit_number = Column(Integer,     nullable=True, comment="Số khám trong ngày/phòng")

    # ── Cờ loại đăng ký ───────────────────────────────────────────────
    is_appointment = Column(Boolean, nullable=False, default=False, server_default="false", comment="Hẹn khám")
    is_online      = Column(Boolean, nullable=False, default=False, server_default="false", comment="Đăng ký online")
    is_referral    = Column(Boolean, nullable=False, default=False, server_default="false", comment="Chuyển tuyến")

    # ── Đối tượng BHYT ────────────────────────────────────────────────
    subject_type = Column(String(10),  nullable=True, comment="Mã đối tượng (1=BHYT, 2=DV…)")
    subject_name = Column(String(100), nullable=True, comment="Tên đối tượng")

    # ── Thẻ BHYT chi tiết ─────────────────────────────────────────────
    insurance_number     = Column(String(20), nullable=True, comment="Số thẻ BHYT")
    insurance_valid_from = Column(Date, nullable=True, comment="Từ ngày hạn thẻ BHYT")
    insurance_valid_to   = Column(Date, nullable=True, comment="Đến ngày hạn thẻ BHYT")
    insurance_expiry     = Column(Date, nullable=True, comment="Hạn thẻ BHYT (legacy)")

    # ── ĐKKCB & giới thiệu ────────────────────────────────────────────
    initial_registration = Column(String(200), nullable=True, comment="Nơi ĐKKCB ban đầu")
    referral_note        = Column(Text,        nullable=True, comment="Nội dung giới thiệu")
    referral_facility    = Column(String(200), nullable=True, comment="Cơ sở giới thiệu/chuyển tuyến")

    # ── Quyền lợi đặc biệt ────────────────────────────────────────────
    high_tech_service     = Column(Boolean, nullable=False, default=False, server_default="false", comment="DVKT cao")
    insurance_5years      = Column(Boolean, nullable=False, default=False, server_default="false", comment="BHYT > 5 năm")
    insurance_5years_date = Column(Date, nullable=True, comment="Ngày tính BHYT > 5 năm")

    # ── Trạng thái đặc biệt & nghèo ───────────────────────────────────
    special_status = Column(String(100), nullable=True, comment="Trạng thái đặc biệt")
    is_near_poor   = Column(Boolean, nullable=False, default=False, server_default="false", comment="Hộ cận nghèo")
    is_poor        = Column(Boolean, nullable=False, default=False, server_default="false", comment="Hộ nghèo")

    # ── Phân loại bệnh nhân ───────────────────────────────────────────
    patient_category = Column(String(50), nullable=True, comment="Người lớn / Trẻ em")
    patient_type     = Column(String(10), nullable=True, comment="Mới / Cũ")

    # ── Trạng thái tiếp đón ───────────────────────────────────────────
    status = Column(
        reception_status_type,
        nullable=False,
        default=ReceptionStatus.PENDING,
        server_default=ReceptionStatus.PENDING.value,
    )

    # ── Trạng thái xử lý tại phòng khám bác sĩ ───────────────────────
    visit_status = Column(
        visit_status_type,
        nullable=False,
        default=VisitStatus.WAITING,
        server_default=VisitStatus.WAITING.value,
    )

    # ── Lâm sàng ──────────────────────────────────────────────────────
    reason      = Column(Text,        nullable=True, comment="Lý do khám / triệu chứng")
    department  = Column(String(100), nullable=True, comment="Khoa/phòng (legacy)")
    doctor_name = Column(String(100), nullable=True, comment="Bác sĩ phụ trách")
    priority    = Column(
        Integer, nullable=False, default=0, server_default="0",
        comment="Ưu tiên: 0=bình thường, 1=ưu tiên, 2=cấp cứu",
    )

    # ── Thời điểm ─────────────────────────────────────────────────────
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    completed_at  = Column(DateTime(timezone=True), nullable=True)

    # ── Nhân viên & ghi chú ───────────────────────────────────────────
    receptionist_name = Column(String(100), nullable=True, comment="Nhân viên tiếp đón")
    internal_note     = Column(Text, nullable=True)
    updated_by        = Column(String(100), nullable=True, comment="Username thực hiện cập nhật cuối")

    # ── Quan hệ ───────────────────────────────────────────────────────
    patient_id = Column(
        Integer, ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    patient = relationship("Patient", back_populates="receptions")

    queue_ticket_id = Column(
        Integer, ForeignKey("queue_tickets.id", ondelete="SET NULL"),
        nullable=True, unique=True, index=True,
    )
    queue_ticket = relationship("QueueTicket", back_populates="reception")

    def __repr__(self) -> str:
        """Trả về chuỗi đại diện ngắn gọn cho debugging."""
        return f"<Reception id={self.id} patient_id={self.patient_id} status={self.status}>"
