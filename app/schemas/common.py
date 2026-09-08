"""
Pydantic schemas dùng chung cho toàn ứng dụng.

Cung cấp các response wrapper tái sử dụng cho phân trang và thông báo đơn giản.
"""
from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Response wrapper chuẩn cho bất kỳ danh sách phân trang nào.

    Sử dụng Python Generics để giữ type-safety:
    ``PaginatedResponse[PatientList]`` sẽ kiểm tra ``items`` là ``List[PatientList]``.

    Attributes:
        items: Danh sách các phần tử trong trang hiện tại.
        total: Tổng số bản ghi (toàn bộ, không chỉ trang hiện tại).
        page: Số trang hiện tại (bắt đầu từ 1).
        page_size: Số bản ghi tối đa mỗi trang.
        total_pages: Tổng số trang (tính từ ``total`` và ``page_size``).
    """

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    """
    Response wrapper cho các thông báo đơn giản (thành công / lỗi).

    Dùng khi endpoint không cần trả dữ liệu phức tạp, chỉ cần thông báo kết quả.

    Attributes:
        message: Nội dung thông báo hiển thị cho người dùng.
        success: ``True`` nếu thao tác thành công, ``False`` nếu có lỗi nghiệp vụ.
    """

    message: str
    success: bool = True
