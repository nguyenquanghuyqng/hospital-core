"""
ORM model số thứ tự hàng chờ.

Mỗi ``QueueTicket`` đại diện cho một lượt lấy số của bệnh nhân.
Sequence được reset về 1 mỗi ngày; ticket_number hiển thị dạng prefix + số
(VD: A001, A002…) trên màn hình LED.

Luồng trạng thái::

    WAITING → CALLING → SERVING → DONE
                      ↘ SKIPPED   (gọi không có mặt)
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Date, func
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.base_model import TimestampMixin
from app.models.enums import QueueStatus, queue_status_type


class QueueTicket(Base, TimestampMixin):
    """
    Bảng ``queue_tickets`` — số thứ tự hàng chờ.

    Attributes:
        id: Khoá chính tự tăng.
        ticket_number: Mã số hiển thị trên màn hình LED (VD: ``A001``).
            Kết hợp prefix + sequence 3 chữ số.
        sequence: Số thứ tự nguyên dùng để sắp xếp trong ngày.
            Reset về 1 mỗi ngày mới.
        issue_date: Ngày cấp số. Dùng để nhóm và reset sequence theo ngày.
        status: Trạng thái hiện tại — xem :class:`~app.models.enums.QueueStatus`.
        service_type: Loại dịch vụ / quầy (tuỳ chọn, VD: ``general``, ``lab``).
        counter_number: Số quầy đang phục vụ (được gán khi gọi số).
        called_at: Thời điểm số được gọi (CALLING).
        served_at: Thời điểm số bắt đầu được phục vụ (SERVING).
        done_at: Thời điểm kết thúc (DONE hoặc SKIPPED).
        note: Ghi chú thêm (tuỳ chọn).
        patient_id: FK tới ``patients`` — có thể NULL nếu chưa liên kết BN.

    Relationships:
        patient: Bệnh nhân liên kết (nếu có).
        reception: Lượt tiếp đón tương ứng (1-1, có thể NULL).
    """

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
    counter_number = Column(Integer,    nullable=True, comment="Số quầy phục vụ")

    # Thời điểm chuyển trạng thái
    called_at = Column(DateTime(timezone=True), nullable=True)
    served_at = Column(DateTime(timezone=True), nullable=True)
    done_at   = Column(DateTime(timezone=True), nullable=True)

    note = Column(Text, nullable=True)

    # Quan hệ
    patient_id = Column(
        Integer, ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    patient   = relationship("Patient",   back_populates="queue_tickets")
    reception = relationship("Reception", back_populates="queue_ticket", uselist=False)

    def __repr__(self) -> str:
        """Trả về chuỗi đại diện ngắn gọn cho debugging."""
        return f"<QueueTicket {self.ticket_number} status={self.status} date={self.issue_date}>"
