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


# ─── CLS Result ───────────────────────────────────────────────────────────────

class ClsResultStatus(str, enum.Enum):
    """Trạng thái kết quả CLS."""
    PENDING    = "pending"    # Chờ thực hiện
    IN_PROCESS = "in_process" # Đang xử lý
    COMPLETED  = "completed"  # Đã có kết quả
    CANCELLED  = "cancelled"  # Huỷ


cls_result_status_type = sa.Enum(
    ClsResultStatus,
    name="cls_result_status",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)


# ─── Bill / Payment ───────────────────────────────────────────────────────────

class BillStatus(str, enum.Enum):
    """Trạng thái hóa đơn viện phí."""
    DRAFT    = "draft"    # Đang tạo
    ISSUED   = "issued"   # Đã phát hành, chờ thanh toán
    PAID     = "paid"     # Đã thanh toán
    PARTIAL  = "partial"  # Thanh toán một phần
    CANCELLED = "cancelled" # Huỷ hóa đơn
    REFUNDED  = "refunded"  # Đã hoàn tiền


class PaymentMethod(str, enum.Enum):
    """Phương thức thanh toán."""
    CASH     = "cash"     # Tiền mặt
    TRANSFER = "transfer" # Chuyển khoản
    CARD     = "card"     # Thẻ ngân hàng
    MOMO     = "momo"     # Ví điện tử MoMo
    VNPAY    = "vnpay"    # VNPay
    ZALOPAY  = "zalopay"  # ZaloPay
    BHYT     = "bhyt"     # BHYT chi trả trực tiếp
    DEFER    = "defer"    # Công nợ / trả sau


bill_status_type = sa.Enum(
    BillStatus,
    name="bill_status",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)

payment_method_type = sa.Enum(
    PaymentMethod,
    name="payment_method",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)


# ─── Appointment ──────────────────────────────────────────────────────────────

class AppointmentStatus(str, enum.Enum):
    """Trạng thái lịch hẹn."""
    SCHEDULED  = "scheduled"  # Đã đặt, chờ xác nhận
    CONFIRMED  = "confirmed"  # Đã xác nhận
    ARRIVED    = "arrived"    # Bệnh nhân đã đến
    COMPLETED  = "completed"  # Đã hoàn tất
    CANCELLED  = "cancelled"  # Đã huỷ
    NO_SHOW    = "no_show"    # Không đến


appointment_status_type = sa.Enum(
    AppointmentStatus,
    name="appointment_status",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)


# ─── National Prescription (BYT / donthuocquocgia.vn) ────────────────────────

class LicenseStatus(str, enum.Enum):
    """
    Trạng thái hành nghề của bác sĩ liên quan đến mã liên thông.

    Ảnh hưởng trực tiếp đến khả năng kê đơn:
    - Chỉ ``ACTIVE`` mới được phép hoàn tất phiếu khám và đẩy đơn.
    """

    ACTIVE    = "active"    # Đang hành nghề — được kê đơn
    SUSPENDED = "suspended" # Tạm dừng hành nghề — không được kê đơn
    REVOKED   = "revoked"   # Bị thu hồi chứng chỉ — không được kê đơn


license_status_col = sa.Enum(
    LicenseStatus,
    name="license_status",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)
"""SQLAlchemy column type cho :class:`LicenseStatus` — PostgreSQL TYPE ``license_status``."""


class DrugCategory(str, enum.Enum):
    """
    Phân loại nhóm thuốc — dùng để xác định ký tự phân loại Z của mã đơn.

    - ``NARCOTIC``       → Z = 'N' (gây nghiện)
    - ``PSYCHOTROPIC``   → Z = 'H' (hướng thần / tiền chất)
    - ``REGULAR``        → Z = 'C' (đơn thường)
    - ``FUNCTIONAL_FOOD``→ bị chặn hoàn toàn khỏi đơn thuốc chính thức
    """

    REGULAR        = "regular"        # Thuốc thường
    NARCOTIC       = "narcotic"       # Thuốc gây nghiện — đơn N
    PSYCHOTROPIC   = "psychotropic"   # Thuốc hướng thần / tiền chất — đơn H
    FUNCTIONAL_FOOD = "functional_food"  # Thực phẩm chức năng — bị chặn


drug_category_col = sa.Enum(
    DrugCategory,
    name="drug_category",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)
"""SQLAlchemy column type cho :class:`DrugCategory` — PostgreSQL TYPE ``drug_category``."""


class PrescriptionType(str, enum.Enum):
    """
    Loại đơn thuốc — xác định ký tự Z cuối mã đơn 14 ký tự.

    Logic xác định tự động:
    - Có bất kỳ thuốc ``NARCOTIC``     → N
    - Có bất kỳ thuốc ``PSYCHOTROPIC`` (và không có NARCOTIC) → H
    - Còn lại → C
    """

    N = "N"  # Gây nghiện
    H = "H"  # Hướng thần / tiền chất
    C = "C"  # Đơn thường


prescription_type_col = sa.Enum(
    PrescriptionType,
    name="prescription_type",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)
"""SQLAlchemy column type cho :class:`PrescriptionType` — PostgreSQL TYPE ``prescription_type``."""


class PrescriptionPushStatus(str, enum.Enum):
    """
    Trạng thái đẩy đơn lên hệ thống quốc gia (donthuocquocgia.vn).

    Vòng đời::

        PENDING → SENDING → SUCCESS
                          ↘ ERROR → (retry) → SENDING → ...
        (admin cancel) → CANCELLED
    """

    PENDING   = "pending"   # Chờ gửi (mới tạo hoặc đang xếp hàng)
    SENDING   = "sending"   # Đang gửi lên hệ thống quốc gia
    SUCCESS   = "success"   # Đã gửi thành công
    ERROR     = "error"     # Gửi thất bại — sẽ retry
    CANCELLED = "cancelled" # Đã huỷ (admin cancel thủ công)


prescription_push_status_col = sa.Enum(
    PrescriptionPushStatus,
    name="prescription_push_status",
    native_enum=True,
    create_type=False,
    values_callable=lambda enum_class: [e.value for e in enum_class],
)
"""SQLAlchemy column type cho :class:`PrescriptionPushStatus` — PostgreSQL TYPE ``prescription_push_status``."""
