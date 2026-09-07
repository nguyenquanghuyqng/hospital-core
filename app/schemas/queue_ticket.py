from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.queue_ticket import QueueStatus


class QueueTicketCreate(BaseModel):
    """Schema tạo số thứ tự mới (bệnh nhân bấm lấy số)."""
    service_type: Optional[str] = Field(
        None,
        max_length=50,
        description="Loại dịch vụ: general / lab / imaging / pharmacy",
        examples=["general"],
    )
    note: Optional[str] = Field(None, description="Ghi chú thêm")


class QueueTicketStatusUpdate(BaseModel):
    """Schema cập nhật trạng thái số thứ tự."""
    status: QueueStatus = Field(..., description="Trạng thái mới")
    counter_number: Optional[int] = Field(None, ge=1, description="Số quầy")
    note: Optional[str] = None


class QueueTicketResponse(BaseModel):
    """Schema trả về chi tiết số thứ tự."""
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
    """Schema danh sách số thứ tự (tóm tắt)."""
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
    Gửi qua WebSocket mỗi khi có thay đổi.
    """
    ticket_number: str = Field(..., description="Số thứ tự hiển thị (VD: A001)")
    counter_number: Optional[int] = Field(None, description="Số quầy")
    status: QueueStatus
    patient_name: Optional[str] = Field(None, description="Tên bệnh nhân (nếu đã đăng ký)")

    model_config = {"from_attributes": True}


class QueueSummary(BaseModel):
    """Tóm tắt hàng đợi theo ngày (dành cho dashboard)."""
    issue_date: date
    total: int
    waiting: int
    calling: int
    serving: int
    done: int
    skipped: int
    current_calling: Optional[str] = Field(None, description="Số thứ tự đang được gọi")
