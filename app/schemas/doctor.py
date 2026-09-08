"""
DTOs (Pydantic schemas) dành riêng cho Doctor endpoints.

Tách ra khỏi ``app/api/v1/endpoints/doctor.py`` để:
- Cho phép tái sử dụng từ các module khác.
- Đảm bảo tiêu chí "DTO/Schema riêng, không trả thẳng ORM Model".
- Tách trách nhiệm: schema layer ≠ API layer.
"""
from datetime import date
from typing import Optional

from pydantic import BaseModel

from app.models.enums import ReceptionStatus, VisitStatus


class VisitStatusUpdate(BaseModel):
    """
    Body request cập nhật trạng thái xử lý bệnh nhân tại phòng khám.

    Attributes:
        visit_status: Trạng thái mới — xem :class:`~app.models.enums.VisitStatus`.
    """

    visit_status: VisitStatus


class TransferRequest(BaseModel):
    """
    Body request chuyển bệnh nhân sang phòng khám khác.

    Attributes:
        clinic_room: Tên / mã phòng khám đích.
        note: Lý do / ghi chú chuyển phòng (tuỳ chọn).
    """

    clinic_room: str
    note: Optional[str] = None


class QueueStatsResponse(BaseModel):
    """
    Response thống kê nhanh hàng đợi bác sĩ theo phòng và ngày.

    Attributes:
        clinic_room: Phòng khám được thống kê.
        visit_date: Ngày thống kê.
        total: Tổng số BN (đang chờ + đã khám).
        waiting: Số BN chờ vào khám.
        cls: Số BN đang làm CLS.
        cls_result: Số BN có kết quả CLS chờ bác sĩ đọc.
        revisit: Số BN hẹn tái khám.
        done: Số BN đã khám xong (COMPLETED).
    """

    clinic_room: str
    visit_date: date
    total: int
    waiting: int
    cls: int
    cls_result: int
    revisit: int
    done: int


class PatientSummary(BaseModel):
    """
    Thông tin hành chính rút gọn của bệnh nhân — hiển thị trong hàng đợi bác sĩ.

    Chỉ chứa các fields cần thiết để bác sĩ nhận diện và tra cứu bệnh nhân
    mà không cần load toàn bộ hồ sơ.
    """

    id: int
    patient_code: Optional[str]
    full_name: str
    date_of_birth: Optional[date]
    birth_year: Optional[int]
    gender: Optional[str]
    ethnicity_name: Optional[str]
    nationality_name: Optional[str]
    occupation: Optional[str]
    address_street: Optional[str]
    address_village: Optional[str]
    address_ward_name: Optional[str]
    address_district_name: Optional[str]
    address_province_name: Optional[str]
    phone: Optional[str]

    model_config = {"from_attributes": True}


class QueueItem(BaseModel):
    """
    Một dòng trong danh sách chờ khám của bác sĩ.

    Kết hợp thông tin lượt tiếp đón và thông tin bệnh nhân tóm tắt.

    Attributes:
        id: ID lượt tiếp đón (reception id).
        visit_number: Số thứ tự khám trong ngày/phòng.
        visit_time: Giờ đăng ký dạng ``HH:MM``.
        visit_status: Trạng thái xử lý tại phòng khám.
        status: Trạng thái tiếp đón (CHECKED_IN / COMPLETED…).
        patient: Thông tin bệnh nhân tóm tắt.
        patient_type: Phân loại bệnh nhân (Mới / Cũ).
        subject_name: Đối tượng chi trả (BHYT / Dịch vụ…).
        priority: Độ ưu tiên (0 thường, 1 ưu tiên, 2 cấp cứu).
    """

    id: int
    visit_number: Optional[int]
    visit_time: Optional[str]
    visit_status: VisitStatus
    status: ReceptionStatus
    patient: PatientSummary
    patient_type: Optional[str]
    subject_name: Optional[str]
    priority: int

    model_config = {"from_attributes": True}
