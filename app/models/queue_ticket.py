"""
Model số thứ tự hàng chờ.

Luồng trạng thái:
  WAITING → CALLING → SERVING → DONE
                    ↘ SKIPPED  (bỏ qua, gọi không có mặt)
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Date, func
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.base_model import TimestampMixin
from app.models.enums import QueueStatus, queue_status_type


class QueueTicket(Base, TimestampMixin):
    __tablename__ = "queue_tickets"

    id = Column(Integer, primary_key=True, index=True)

    # Số thứ tự hiển thị (VD: A001)
    ticket_number = Column(String(10), nullable=False, index=True, comment="Số thứ tự")

    # Số thứ tự nguyên để sắp xếp
    sequence = Column(Integer, nullable=False, comment="Thứ tự số nguyên")

    # Ngày cấp số (reset mỗi ngày)
    issue_date = Column(
        Date, nullable=False,
        server_default=func.current_date(),
        comment="Ngày cấp số",
    )

    # Trạng thái — dùng singleton type từ enums.py, create_type=False
    status = Column(
        queue_status_type,
        nullable=False,
        default=QueueStatus.WAITING,
        server_default=QueueStatus.WAITING.value,
    )

    # Loại dịch vụ / quầy
    service_type   = Column(String(50), nullable=True, comment="Loại dịch vụ")
    counter_number = Column(Integer, nullable=True, comment="Số quầy phục vụ")

    # Thời điểm
    called_at = Column(DateTime(timezone=True), nullable=True)
    served_at = Column(DateTime(timezone=True), nullable=True)
    done_at   = Column(DateTime(timezone=True), nullable=True)

    note = Column(Text, nullable=True)

    # Quan hệ
    patient_id = Column(
        Integer, ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    patient   = relationship("Patient", back_populates="queue_tickets")
    reception = relationship("Reception", back_populates="queue_ticket", uselist=False)

    def __repr__(self) -> str:
        return f"<QueueTicket {self.ticket_number} status={self.status} date={self.issue_date}>"
