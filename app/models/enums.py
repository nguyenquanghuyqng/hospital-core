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


# ─── Visit Status (trạng thái xử lý tại phòng khám) ──────────────────────────

class VisitStatus(str, enum.Enum):
    """Trạng thái xử lý bệnh nhân tại phòng khám bác sĩ."""
    WAITING    = "waiting"     # Chờ khám (mặc định)
    CLS        = "cls"         # Đi làm CLS (cận lâm sàng)
    CLS_RESULT = "cls_result"  # Có kết quả CLS
    REVISIT    = "revisit"     # Tái khám
    DONE       = "done"        # Đã khám xong


visit_status_type = sa.Enum(
    VisitStatus,
    name="visit_status",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)


# ─── Examination (Phiếu khám bệnh) ───────────────────────────────────────────

class ExaminationStatus(str, enum.Enum):
    """Trạng thái phiếu khám."""
    DRAFT     = "draft"      # Đang nhập liệu
    SAVED     = "saved"      # Đã lưu tạm
    COMPLETED = "completed"  # Kết thúc khám


class DispositionType(str, enum.Enum):
    """Hướng xử trí sau khám (loại trừ lẫn nhau)."""
    EMERGENCY        = "emergency"        # Cấp cứu
    OUTPATIENT       = "outpatient"       # Điều trị ngoại trú
    REVISIT          = "revisit"          # Hẹn tái khám
    INPATIENT_WARD   = "inpatient_ward"   # Chuyển phòng lưu
    INPATIENT        = "inpatient"        # Nhập viện
    TRANSFER_OUT     = "transfer_out"     # Chuyển tuyến
    DECEASED         = "deceased"         # Tử vong
    TRANSFER_CLINIC  = "transfer_clinic"  # Chuyển phòng khám
    LEAVE_AMA        = "leave_ama"        # Bỏ về
    DISCHARGED       = "discharged"       # Khám xong cho về
    CHRONIC_SCRIPT   = "chronic_script"   # Cấp toa bệnh mãn tính


class PaymentType(str, enum.Enum):
    """Loại chi trả cho từng dòng chỉ định/kê đơn."""
    BHYT      = "bhyt"       # BHYT
    FEE       = "fee"        # Thu phí
    REQUEST   = "request"    # Yêu cầu
    HEALTH    = "health"     # Khám sức khoẻ
    CONSUME   = "consume"    # Hao phí
    UNDER6    = "under6"     # Trẻ dưới 6 tuổi
    VACCINE   = "vaccine"    # Tiêm chủng
    FREE      = "free"       # Miễn
    DEFER     = "defer"      # Trả sau


examination_status_type = sa.Enum(
    ExaminationStatus,
    name="examination_status",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)

disposition_type_col = sa.Enum(
    DispositionType,
    name="disposition_type",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)

payment_type_col = sa.Enum(
    PaymentType,
    name="payment_type",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)
