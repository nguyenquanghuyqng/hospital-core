"""
Định nghĩa tất cả enum dùng trong hệ thống.

Single source of truth: mọi model, schema, và migration đều import từ đây.

Chiến lược lưu trữ enum trong PostgreSQL
-----------------------------------------
Mỗi enum Python được ánh xạ thành một ``sa.Enum`` column type với:

- ``native_enum=True``   → SQLAlchemy dùng PostgreSQL TYPE thật sự (``CREATE TYPE … AS ENUM``).
- ``create_type=False``  → SQLAlchemy **không** tự phát sinh DDL ``CREATE TYPE``;
  thay vào đó migration 0001 tạo TYPE bằng raw SQL để kiểm soát hoàn toàn.
- ``values_callable``    → dùng ``.value`` (lowercase string) thay vì ``.name`` (uppercase).

Ưu điểm: hiệu năng tốt hơn VARCHAR + CHECK constraint, chiếm ít storage hơn,
đồng thời tránh lỗi ``DuplicateObject`` khi migration chạy lại.
"""
import enum
import sqlalchemy as sa


# ─── Queue ────────────────────────────────────────────────────────────────────

class QueueStatus(str, enum.Enum):
    """
    Trạng thái vòng đời của một số thứ tự hàng chờ.

    Luồng chuyển trạng thái::

        WAITING → CALLING → SERVING → DONE
                          ↘ SKIPPED   (gọi không có mặt)
    """

    WAITING = "waiting"   # Đang chờ đến lượt
    CALLING = "calling"   # Đang được gọi (hiển thị trên màn hình LED)
    SERVING = "serving"   # Đang được phục vụ tại quầy
    DONE    = "done"      # Hoàn thành
    SKIPPED = "skipped"   # Bỏ qua (gọi không có mặt)


queue_status_type = sa.Enum(
    QueueStatus,
    name="queue_status",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)
"""SQLAlchemy column type cho :class:`QueueStatus` — tham chiếu PostgreSQL TYPE ``queue_status``."""


# ─── Reception ────────────────────────────────────────────────────────────────

class ReceptionStatus(str, enum.Enum):
    """
    Trạng thái vòng đời của một lượt tiếp đón bệnh nhân.

    Luồng chuyển trạng thái::

        PENDING → CHECKED_IN → COMPLETED
                             ↘ CANCELLED
    """

    PENDING    = "pending"     # Đã đăng ký, chờ nhân viên tiếp nhận
    CHECKED_IN = "checked_in"  # Đã tiếp nhận, đang chờ vào khám
    COMPLETED  = "completed"   # Hoàn tất lượt khám
    CANCELLED  = "cancelled"   # Huỷ lượt đăng ký


reception_status_type = sa.Enum(
    ReceptionStatus,
    name="reception_status",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)
"""SQLAlchemy column type cho :class:`ReceptionStatus` — tham chiếu PostgreSQL TYPE ``reception_status``."""


# ─── Visit Status ─────────────────────────────────────────────────────────────

class VisitStatus(str, enum.Enum):
    """
    Trạng thái xử lý chi tiết của bệnh nhân tại phòng khám bác sĩ.

    Phản ánh vị trí thực tế của bệnh nhân trong quy trình khám::

        WAITING → CLS → CLS_RESULT → REVISIT → DONE
    """

    WAITING    = "waiting"     # Chờ vào khám (mặc định khi check-in)
    CLS        = "cls"         # Đang đi làm cận lâm sàng (xét nghiệm, chụp X-quang…)
    CLS_RESULT = "cls_result"  # Đã có kết quả CLS, chờ bác sĩ đọc kết quả
    REVISIT    = "revisit"     # Bác sĩ hẹn tái khám
    DONE       = "done"        # Đã khám xong, rời phòng khám


visit_status_type = sa.Enum(
    VisitStatus,
    name="visit_status",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)
"""SQLAlchemy column type cho :class:`VisitStatus` — tham chiếu PostgreSQL TYPE ``visit_status``."""


# ─── Examination ──────────────────────────────────────────────────────────────

class ExaminationStatus(str, enum.Enum):
    """
    Trạng thái vòng đời của phiếu khám bệnh.

    Luồng chuyển trạng thái::

        DRAFT → SAVED → COMPLETED
    """

    DRAFT     = "draft"      # Đang nhập liệu, chưa lưu chính thức
    SAVED     = "saved"      # Đã lưu tạm, có thể tiếp tục chỉnh sửa
    COMPLETED = "completed"  # Kết thúc khám, không thể chỉnh sửa


class DispositionType(str, enum.Enum):
    """
    Hướng xử trí sau khám — các giá trị loại trừ lẫn nhau.

    Bác sĩ chọn đúng một hướng xử trí khi kết thúc phiếu khám.
    """

    EMERGENCY        = "emergency"        # Cấp cứu ngay
    OUTPATIENT       = "outpatient"       # Điều trị ngoại trú
    REVISIT          = "revisit"          # Hẹn tái khám
    INPATIENT_WARD   = "inpatient_ward"   # Chuyển vào phòng lưu
    INPATIENT        = "inpatient"        # Nhập viện điều trị nội trú
    TRANSFER_OUT     = "transfer_out"     # Chuyển tuyến lên tuyến trên
    DECEASED         = "deceased"         # Tử vong
    TRANSFER_CLINIC  = "transfer_clinic"  # Chuyển sang phòng khám khác trong cùng cơ sở
    LEAVE_AMA        = "leave_ama"        # Bỏ về (Against Medical Advice)
    DISCHARGED       = "discharged"       # Khám xong, cho về
    CHRONIC_SCRIPT   = "chronic_script"   # Cấp toa bệnh mãn tính


class PaymentType(str, enum.Enum):
    """
    Loại chi trả áp dụng cho từng dòng kê đơn hoặc chỉ định CLS.

    Xác định nguồn thanh toán và tỷ lệ BHYT chi trả.
    """

    BHYT      = "bhyt"       # Bảo hiểm y tế chi trả
    FEE       = "fee"        # Thu phí dịch vụ
    REQUEST   = "request"    # Theo yêu cầu bệnh nhân
    HEALTH    = "health"     # Khám sức khoẻ định kỳ
    CONSUME   = "consume"    # Hao phí (vật tư tiêu hao)
    UNDER6    = "under6"     # Trẻ em dưới 6 tuổi (miễn viện phí)
    VACCINE   = "vaccine"    # Tiêm chủng
    FREE      = "free"       # Miễn phí
    DEFER     = "defer"      # Trả sau


examination_status_type = sa.Enum(
    ExaminationStatus,
    name="examination_status",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)
"""SQLAlchemy column type cho :class:`ExaminationStatus` — tham chiếu PostgreSQL TYPE ``examination_status``."""

disposition_type_col = sa.Enum(
    DispositionType,
    name="disposition_type",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)
"""SQLAlchemy column type cho :class:`DispositionType` — tham chiếu PostgreSQL TYPE ``disposition_type``."""

payment_type_col = sa.Enum(
    PaymentType,
    name="payment_type",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)
"""SQLAlchemy column type cho :class:`PaymentType` — tham chiếu PostgreSQL TYPE ``payment_type``."""
