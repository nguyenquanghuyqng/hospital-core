from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Schema chung cho danh sách phân trang."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    """Schema trả về message đơn giản."""
    message: str
    success: bool = True
