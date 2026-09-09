"""
ORM model cho lịch hẹn khám.

Độc lập với Examination/Reception — dùng cho đặt hẹn trước,
hẹn tái khám sau khi hoàn tất phiếu khám.

Quan hệ::

    Patient 1 ──── N  Appointment
    Appointment N ──── 1  User (doctor)
    Examination 1 ──── 0..1  Appointment  (revisit)
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Text,
    Boolean, ForeignKey, func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.base_model import TimestampMixin
from app.models.enums import AppointmentStatus, appointment_status_type


class Appointment(Base, TimestampMixin):
    """
    Bảng ``appointments`` — lịch hẹn khám độc lập.

    Dùng cho:
    - Đặt hẹn mới (qua lễ tân hoặc bệnh nhân tự đặt).
    - Hẹn tái khám sau khi bác sĩ kết thúc phiếu khám (examination_id != null).

    Attributes:
        appointment_no: Mã lịch hẹn (tự sinh, HA2026XXXXXX).
        patient_id: FK tới ``patients``.
        doctor_id: FK tới ``users`` (bác sĩ được hẹn).
        examination_id: FK tới ``examinations`` (nếu là tái khám).
        scheduled_date: Ngày hẹn.
        scheduled_time: Giờ hẹn (text, VD: "08:30").
        status: Trạng thái lịch hẹn.
        appointment_type: Loại hẹn (new | revisit | followup).
        reason: Lý do khám / mô tả triệu chứng.
        doctor_name: Tên bác sĩ (snapshot).
        department: Khoa/phòng.
        clinic_room: Phòng khám.
        note: Ghi chú nội bộ.
        patient_note: Ghi chú của bệnh nhân.
        created_by: Username người tạo lịch hẹn.
        confirmed_at: Thời điểm xác nhận.
        arrived_at: Thời điểm bệnh nhân đến.
        completed_at: Thời điểm hoàn tất.
        cancelled_at: Thời điểm huỷ.
        cancel_reason: Lý do huỷ.
        is_reminded: Đã gửi nhắc lịch chưa.
    """

    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)

    appointment_no = Column(String(20), unique=True, index=True, nullable=False,
                            comment="Mã lịch hẹn HA2026XXXXXX")

    # ── Liên kết ──────────────────────────────────────────────────────────────
    patient_id     = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    doctor_id      = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                            nullable=True, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id", ondelete="SET NULL"),
                            nullable=True, index=True,
                            comment="Phiếu khám gốc nếu là lịch tái khám")

    # ── Thời gian hẹn ─────────────────────────────────────────────────────────
    scheduled_date = Column(Date, nullable=False, index=True, comment="Ngày hẹn")
    scheduled_time = Column(String(10), nullable=True, comment="Giờ hẹn (HH:MM)")

    # ── Thông tin hẹn ─────────────────────────────────────────────────────────
    status           = Column(
        appointment_status_type,
        nullable=False,
        default=AppointmentStatus.SCHEDULED,
        server_default=AppointmentStatus.SCHEDULED.value,
    )
    appointment_type = Column(String(20), nullable=False, server_default="'new'",
                              comment="new | revisit | followup")
    reason           = Column(Text, nullable=True, comment="Lý do khám / triệu chứng")
    doctor_name      = Column(String(100), nullable=True, comment="Tên bác sĩ (snapshot)")
    department       = Column(String(100), nullable=True, comment="Khoa/phòng")
    clinic_room      = Column(String(50),  nullable=True, comment="Phòng khám")
    note             = Column(Text, nullable=True, comment="Ghi chú nội bộ")
    patient_note     = Column(Text, nullable=True, comment="Ghi chú của bệnh nhân")
    created_by       = Column(String(100), nullable=True, comment="Username tạo lịch")

    # ── Mốc thời gian ─────────────────────────────────────────────────────────
    confirmed_at  = Column(DateTime(timezone=True), nullable=True)
    arrived_at    = Column(DateTime(timezone=True), nullable=True)
    completed_at  = Column(DateTime(timezone=True), nullable=True)
    cancelled_at  = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(Text, nullable=True)
    is_reminded   = Column(Boolean, nullable=False, default=False, server_default="false",
                           comment="Đã gửi nhắc lịch")

    # ── Quan hệ ───────────────────────────────────────────────────────────────
    patient     = relationship("Patient", foreign_keys=[patient_id], lazy="select")
    doctor      = relationship("User",    foreign_keys=[doctor_id],  lazy="select")
    examination = relationship("Examination", foreign_keys=[examination_id], lazy="select")

    def __repr__(self) -> str:
        return (
            f"<Appointment {self.appointment_no} "
            f"patient={self.patient_id} date={self.scheduled_date} "
            f"status={self.status}>"
        )
