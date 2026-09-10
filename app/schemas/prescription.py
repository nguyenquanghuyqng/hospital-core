"""
Pydantic schemas cho đơn thuốc điện tử chuẩn Bộ Y tế (donthuocquocgia.vn).

Cấu trúc::

    PrescriptionCreate   — bác sĩ/hệ thống tạo đơn khi hoàn tất phiếu khám
    PrescriptionUpdate   — cập nhật thông tin người nhận, đợt dùng thuốc
    PrescriptionResponse — response đầy đủ trả về client
    PrescriptionList     — tóm tắt dùng cho bảng danh sách
    PrescriptionDashboard— thống kê tỷ lệ gửi thành công/thất bại cho admin
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator

from app.models.enums import PrescriptionType, PrescriptionPushStatus


# ─── Create ───────────────────────────────────────────────────────────────────

class PrescriptionCreate(BaseModel):
    """
    Schema tạo đơn thuốc — được gọi nội bộ khi bác sĩ complete phiếu khám.

    Phần lớn fields được hệ thống tự điền từ dữ liệu phiếu khám + bệnh nhân.
    Bác sĩ chỉ cần cung cấp các trường không có sẵn: guardian_name, treatment dates.

    Validation bắt buộc (trước khi tạo mã):
    - ``patient_phone`` luôn bắt buộc.
    - ``patient_weight_kg`` bắt buộc nếu BN < 72 tháng tuổi.
    - ``guardian_name`` bắt buộc nếu BN < 72 tháng tuổi.
    - ``treatment_from/to`` bắt buộc với đơn N/H.
    - ``recipient_cccd`` bắt buộc với đơn N/H.
    """

    examination_id:     int
    patient_id:         int
    doctor_id:          Optional[int] = None

    # Hình thức điều trị
    is_inpatient:       bool = Field(False, description="True=Nội trú, False=Ngoại trú")

    # Đợt dùng thuốc (bắt buộc N/H — validate trong service)
    treatment_from:     Optional[date] = Field(None, description="Đợt dùng thuốc từ ngày")
    treatment_to:       Optional[date] = Field(None, description="Đợt dùng thuốc đến ngày")

    # Thông tin BN
    patient_phone:      Optional[str] = Field(None, max_length=20)
    patient_weight_kg:  Optional[Decimal] = Field(None, gt=0, description="Cân nặng kg")
    patient_gender_code: Optional[int] = Field(None, ge=1, le=3, description="1=Nam 2=Nữ 3=Khác")
    guardian_name:      Optional[str] = Field(None, max_length=100)

    # Người nhận (bắt buộc N/H)
    recipient_cccd:     Optional[str] = Field(None, max_length=12)
    recipient_name:     Optional[str] = Field(None, max_length=100)

    # Snapshot bác sĩ (tự điền)
    doctor_name:          Optional[str] = Field(None, max_length=100)
    doctor_national_code: Optional[str] = Field(None, max_length=20)


# ─── Update ───────────────────────────────────────────────────────────────────

class PrescriptionUpdate(BaseModel):
    """
    Schema cập nhật đơn thuốc — chỉ cho phép sửa thông tin phụ trợ,
    không cho phép sửa mã đơn hoặc trạng thái đẩy.

    Chỉ dùng được khi ``push_status != 'success'``.
    """

    is_inpatient:       Optional[bool]    = None
    treatment_from:     Optional[date]    = None
    treatment_to:       Optional[date]    = None
    patient_phone:      Optional[str]     = Field(None, max_length=20)
    patient_weight_kg:  Optional[Decimal] = None
    patient_gender_code: Optional[int]   = Field(None, ge=1, le=3)
    guardian_name:      Optional[str]     = Field(None, max_length=100)
    recipient_cccd:     Optional[str]     = Field(None, max_length=12)
    recipient_name:     Optional[str]     = Field(None, max_length=100)


# ─── Response ─────────────────────────────────────────────────────────────────

class PrescriptionItemSummary(BaseModel):
    """Tóm tắt một dòng thuốc trong response đơn thuốc."""
    id:                int
    item_name:         str
    unit:              Optional[str] = None
    quantity:          Decimal
    usage_instruction: Optional[str] = None
    valid_from:        Optional[date] = None
    valid_to:          Optional[date] = None
    model_config = {"from_attributes": True}


class PrescriptionResponse(BaseModel):
    """
    Schema response đầy đủ của một đơn thuốc.

    Bao gồm mã đơn, trạng thái đẩy, thông tin BN, và danh sách thuốc.
    """

    id:               int
    examination_id:   int
    patient_id:       int
    doctor_id:        Optional[int] = None

    # Mã đơn
    prescription_code:  Optional[str] = None
    facility_code:      Optional[str] = None
    prescription_type:  PrescriptionType
    push_status:        PrescriptionPushStatus

    # Hình thức điều trị
    is_inpatient:       bool

    # Đợt dùng thuốc
    treatment_from:     Optional[date] = None
    treatment_to:       Optional[date] = None

    # BN snapshot
    patient_phone:       Optional[str]     = None
    patient_weight_kg:   Optional[Decimal] = None
    patient_gender_code: Optional[int]     = None
    guardian_name:       Optional[str]     = None

    # Người nhận N/H
    recipient_cccd:     Optional[str] = None
    recipient_name:     Optional[str] = None

    # Hệ thống quốc gia
    national_ref_id:    Optional[str] = None
    sent_at:            Optional[datetime] = None
    sold_at:            Optional[datetime] = None

    # Retry info
    retry_count:        int
    retry_at:           Optional[datetime] = None
    error_log:          Optional[str] = None

    # Bác sĩ snapshot
    doctor_name:          Optional[str] = None
    doctor_national_code: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PrescriptionList(BaseModel):
    """Tóm tắt đơn thuốc — dùng cho bảng danh sách."""
    id:               int
    examination_id:   int
    prescription_code: Optional[str] = None
    prescription_type: PrescriptionType
    push_status:       PrescriptionPushStatus
    is_inpatient:      bool
    patient_phone:     Optional[str] = None
    doctor_name:       Optional[str] = None
    sent_at:           Optional[datetime] = None
    retry_count:       int
    created_at:        datetime
    model_config = {"from_attributes": True}


# ─── Dashboard ────────────────────────────────────────────────────────────────

class PrescriptionDashboard(BaseModel):
    """
    Thống kê tỷ lệ gửi đơn — dùng cho admin dashboard giám sát liên thông.
    """
    total_today:     int = Field(description="Tổng đơn tạo hôm nay")
    pending:         int = Field(description="Chờ gửi")
    success:         int = Field(description="Đã gửi thành công")
    error:           int = Field(description="Gửi lỗi (kể cả đang retry)")
    cancelled:       int = Field(description="Đã huỷ")
    success_rate_pct: float = Field(description="Tỷ lệ thành công % (success / total_today)")
    avg_retry_count:  float = Field(description="Số lần retry trung bình")
    last_success_at:  Optional[datetime] = Field(None, description="Lần gửi thành công gần nhất")
    facility_code:    Optional[str] = None
    is_facility_code_configured: bool = Field(
        description="False = chưa cấu hình national_facility_code → cảnh báo admin"
    )
