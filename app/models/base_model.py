from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func

from app.db.base import Base


class TimestampMixin:
    """Mixin cung cấp created_at và updated_at tự động."""

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
