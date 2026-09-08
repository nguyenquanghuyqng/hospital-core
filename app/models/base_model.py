"""
Mixin dùng chung cho tất cả ORM models.

Cung cấp các cột audit timestamp tự động được quản lý bởi database server,
không phụ thuộc vào timezone của application server.
"""
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

from app.db.base import Base


class TimestampMixin:
    """
    Mixin tự động thêm hai cột audit timestamp vào bất kỳ model nào kế thừa.

    Cả hai cột đều dùng ``server_default`` / ``onupdate`` để giá trị
    được sinh bởi PostgreSQL server (``now()``), đảm bảo nhất quán
    ngay cả khi nhiều application instance chạy song song.

    Attributes:
        created_at: Thời điểm bản ghi được tạo lần đầu (UTC, có timezone).
            Không bao giờ thay đổi sau khi insert.
        updated_at: Thời điểm bản ghi được cập nhật lần cuối (UTC, có timezone).
            Tự động cập nhật mỗi khi row được UPDATE.
    """

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
