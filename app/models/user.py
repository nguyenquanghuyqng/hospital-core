"""
Model tài khoản người dùng (bác sĩ / y tá / admin).
"""
from sqlalchemy import Column, Integer, String, Boolean
from app.db.base import Base
from app.models.base_model import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id       = Column(Integer, primary_key=True, index=True)
    username = Column(String(50),  nullable=False, unique=True, index=True, comment="Tên đăng nhập")
    hashed_password = Column(String(200), nullable=False)
    full_name    = Column(String(100), nullable=True,  comment="Họ tên hiển thị")
    role         = Column(String(20),  nullable=False, default="doctor", server_default="doctor",
                          comment="doctor | nurse | admin")
    clinic_room  = Column(String(50),  nullable=True,  comment="Phòng khám phụ trách")
    is_active    = Column(Boolean,     nullable=False, default=True, server_default="true")

    def __repr__(self) -> str:
        return f"<User {self.username} role={self.role}>"
