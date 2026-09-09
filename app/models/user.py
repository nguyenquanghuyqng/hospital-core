"""
ORM model tài khoản người dùng hệ thống.

Người dùng có thể là bác sĩ, y tá/điều dưỡng, hoặc admin.
Role quyết định quyền truy cập vào các nhóm endpoint khác nhau.
"""
from sqlalchemy import Column, Integer, String, Boolean
from app.db.base import Base
from app.models.base_model import TimestampMixin


class User(Base, TimestampMixin):
    """
    Bảng ``users`` — tài khoản đăng nhập của nhân viên y tế.

    Attributes:
        id: Khoá chính tự tăng.
        username: Tên đăng nhập, duy nhất trong hệ thống.
        hashed_password: Mật khẩu đã hash bằng bcrypt, không bao giờ lưu plain-text.
        full_name: Họ tên hiển thị (tuỳ chọn, dùng trong phiếu khám).
        role: Vai trò — ``doctor`` | ``nurse`` | ``admin``.
            Ảnh hưởng trực tiếp đến phân quyền API.
        clinic_room: Phòng khám mặc định của bác sĩ.
            Dùng để lọc danh sách hàng đợi tại trang doctor.
        is_active: Trạng thái tài khoản. ``False`` = bị vô hiệu hoá,
            không thể đăng nhập dù mật khẩu đúng.
    """

    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(50),  nullable=False, unique=True, index=True, comment="Tên đăng nhập")
    hashed_password = Column(String(200), nullable=False)
    full_name       = Column(String(100), nullable=True,  comment="Họ tên hiển thị")
    role            = Column(String(20),  nullable=False, default="doctor", server_default="doctor",
                             comment="doctor | nurse | receptionist | cashier | admin")
    clinic_room     = Column(String(50),  nullable=True,  comment="Phòng khám phụ trách")
    is_active       = Column(Boolean,     nullable=False, default=True, server_default="true")

    def __repr__(self) -> str:
        """Trả về chuỗi đại diện ngắn gọn cho debugging."""
        return f"<User {self.username} role={self.role}>"
