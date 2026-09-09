"""
Khai báo SQLAlchemy declarative base và import tất cả models.

File này phục vụ hai mục đích:
1. Cung cấp ``Base`` — lớp cha chung cho tất cả ORM models.
2. Import toàn bộ model modules để Alembic ``autogenerate`` phát hiện
   được schema thay đổi khi chạy ``alembic revision --autogenerate``.

Mọi model mới phải được import ở đây để Alembic nhận diện.
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import all models here so Alembic can detect them
from app.models import patient, queue_ticket, reception, user, examination, catalog  # noqa: F401, E402
