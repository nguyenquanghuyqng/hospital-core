"""
Pydantic schemas cho số thứ tự hàng chờ.

Cung cấp các schema để tạo số thứ tự, cập nhật trạng thái,
và các response format khác nhau (chi tiết, danh sách, màn hình LED, dashboard).
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.queue_ticket import QueueStatus


class QueueTicketCreate(BaseModel):
    """
    Schema tạo số thứ tự mới — bệnh nhân bấm lấy số tại kiosk.

    Chỉ cần truyền ``service_type`` (tuỳ chọn) và ``note`` (tuỳ chọn).
    ``ticket_number``, ``sequence``, ``issue_date``, và ``status``
    được server tự sinh trong :meth:`~app.crud.queue_ticket.CRUDQueueTicket.create_ticket`.

    Attributes:
        service_type: Loại dịch vụ cần phục vụ (VD: ``"general"``, ``"lab"``).
        note: Ghi chú thêm của bệnh nhân (tuỳ chọn).
    """

    service_type: Optional[str] = Field(
        None,
        max_length=50,
        description="Loại dịch vụ: general / lab / imaging / pharmacy",
        examples=["general"],
    )
    note: Optional[str] = Field(None, description="Ghi chú thêm")


class QueueTicketStatusUpdate(BaseModel):
    """
    Schema cập nhật trạng thái số thứ tự thủ công.

    Dùng bởi nhân viên hoặc hệ thống để chuyển trạng thái số thứ tự.
    Timestamp tương ứng được tự động ghi bởi CRUD layer.

    Attributes:
        status: Trạng thái mới cần chuyển sang.
        counter_number: Số quầy đang phục vụ (tuỳ chọn, gán khi CALLING/SERVING).
        note: Ghi chú thêm (tuỳ chọn).
    """

    status: QueueStatus = Field(..., description="Trạng thái mới")
    counter_number: Optional[int] = Field(None, ge=1, description="Số quầy")
    note: Optional[str] = None


class QueueTicketResponse(BaseModel):
    """
    Schema response chi tiết đầy đủ một số thứ tự.

    Trả về sau khi tạo mới hoặc lấy theo ID.
    Bao gồm tất cả timestamps để client có thể tính thời gian chờ.

    Attributes:
        id: ID số thứ tự.
        ticket_number: Mã hiển thị (VD: ``"A001"``).
        sequence: Số thứ tự nguyên để sắp xếp.
        issue_date: Ngày cấp số.
        status: Trạng thái hiện tại.
        service_type: Loại dịch vụ (tuỳ chọn).
        counter_number: Số quầy đang phục vụ (tuỳ chọn).
        called_at: Thời điểm được gọi (CALLING).
        served_at: Thời điểm bắt đầu phục vụ (SERVING).
        done_at: Thời điểm kết thúc (DONE/SKIPPED).
    """

    id: int
    ticket_number: str
    sequence: int
    issue_date: date
    status: QueueStatus
    service_type: Optional[str] = None
    counter_number: Optional[int] = None
    called_at: Optional[datetime] = None
    served_at: Optional[datetime] = None
    done_at: Optional[datetime] = None
    note: Optional[str] = None
    patient_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QueueTicketList(BaseModel):
    """
    Schema tóm tắt số thứ tự — dùng cho bảng danh sách.

    Bỏ qua các timestamps chi tiết (called_at, served_at, done_at)
    để giảm payload khi trả danh sách dài.
    """

    id: int
    ticket_number: str
    sequence: int
    issue_date: date
    status: QueueStatus
    service_type: Optional[str] = None
    counter_number: Optional[int] = None
    patient_id: Optional[int] = None

    model_config = {"from_attributes": True}


class QueueDisplayItem(BaseModel):
    """
    Schema dành riêng cho màn hình LED hiển thị số thứ tự.

    Được gửi qua WebSocket (room ``"display"``) mỗi khi có số mới được gọi.
    Chỉ chứa thông tin cần thiết cho màn hình hiển thị công khai.

    Attributes:
        ticket_number: Số thứ tự hiển thị lớn trên màn hình (VD: ``"A001"``).
        counter_number: Số quầy bệnh nhân cần đến (tuỳ chọn).
        status: Trạng thái hiện tại của số thứ tự.
        patient_name: Tên bệnh nhân hiển thị kèm (nếu đã đăng ký).
    """

    ticket_number: str = Field(..., description="Số thứ tự hiển thị (VD: A001)")
    counter_number: Optional[int] = Field(None, description="Số quầy")
    status: QueueStatus
    patient_name: Optional[str] = Field(None, description="Tên bệnh nhân (nếu đã đăng ký)")

    model_config = {"from_attributes": True}


class QueueSummary(BaseModel):
    """
    Schema tóm tắt hàng đợi theo ngày — dành cho dashboard và broadcast WebSocket.

    Trả về số lượng theo từng trạng thái và số thứ tự đang được gọi hiện tại.

    Attributes:
        issue_date: Ngày thống kê.
        total: Tổng số thứ tự đã cấp trong ngày.
        waiting: Số đang chờ.
        calling: Số đang được gọi (thường là 1 hoặc 0).
        serving: Số đang được phục vụ.
        done: Số đã hoàn thành.
        skipped: Số đã bỏ qua.
        current_calling: ``ticket_number`` đang được gọi, hoặc ``None`` nếu không có.
    """

    issue_date: date
    total: int
    waiting: int
    calling: int
    serving: int
    done: int
    skipped: int
    current_calling: Optional[str] = Field(None, description="Số thứ tự đang được gọi")
