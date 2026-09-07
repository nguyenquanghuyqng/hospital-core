"""
Định nghĩa tất cả enum dùng trong hệ thống.

Single source of truth: mọi model, schema, migration đều import từ đây.

Chiến lược lưu trữ enum trong PostgreSQL:
- native_enum=True  → lưu dưới dạng PostgreSQL TYPE (CREATE TYPE … AS ENUM)
- native_enum=False → lưu dưới dạng VARCHAR với CHECK constraint
  → SQLAlchemy KHÔNG tự phát sinh CREATE TYPE trong bất kỳ context nào,
    tránh hoàn toàn lỗi DuplicateObject khi migration chạy.

Migration 0001 dùng native_enum=True + raw SQL để tạo TYPE PostgreSQL
thực sự (hiệu năng tốt hơn, chiếm ít storage hơn VARCHAR).
Models và schemas dùng native_enum=False cho runtime để tránh conflict.
"""
import enum
import sqlalchemy as sa


# ─── Queue ────────────────────────────────────────────────────────────────────

class QueueStatus(str, enum.Enum):
    """Trạng thái số thứ tự hàng chờ."""
    WAITING = "waiting"   # Đang chờ
    CALLING = "calling"   # Đang gọi (hiển thị LED)
    SERVING = "serving"   # Đang phục vụ tại quầy
    DONE    = "done"      # Hoàn thành
    SKIPPED = "skipped"   # Bỏ qua (gọi không có mặt)


# native_enum=True + create_type=False: dùng PostgreSQL TYPE đã tạo bởi migration
# values_callable: dùng .value (lowercase) thay vì .name (uppercase)
queue_status_type = sa.Enum(
    QueueStatus,
    name="queue_status",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)


# ─── Reception ────────────────────────────────────────────────────────────────

class ReceptionStatus(str, enum.Enum):
    """Trạng thái lượt tiếp đón bệnh nhân."""
    PENDING    = "pending"     # Chờ tiếp đón
    CHECKED_IN = "checked_in"  # Đã tiếp nhận, đang chờ khám
    COMPLETED  = "completed"   # Hoàn tất
    CANCELLED  = "cancelled"   # Huỷ


reception_status_type = sa.Enum(
    ReceptionStatus,
    name="reception_status",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)
