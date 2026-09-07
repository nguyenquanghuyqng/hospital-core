from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.reception import ReceptionStatus
from app.schemas.patient import PatientCreate, PatientResponse, PatientList


# ─────────────────────────────────────────────────────────────
# Create
# ─────────────────────────────────────────────────────────────
class ReceptionCreate(BaseModel):
    """
    Schema tạo mới một lần tiếp đón.
    Nhân viên có thể nhập patient_id (đã có) hoặc patient_data (bệnh nhân mới).
    """
    # ── Bệnh nhân ────────────────────────────────────────────────────
    patient_id:   Optional[int]           = Field(None, description="ID bệnh nhân đã có")
    patient_data: Optional[PatientCreate] = Field(None, description="Tạo bệnh nhân mới đồng thời")

    # ── II. Ngày giờ đăng ký ─────────────────────────────────────────
    visit_time:  Optional[str] = Field(None, max_length=8,  description="Giờ đăng ký (HH:MM)")

    # ── Phòng khám & số khám ─────────────────────────────────────────
    clinic_room:  Optional[str] = Field(None, max_length=50, description="Phòng khám")
    visit_number: Optional[int] = Field(None, description="Số khám")

    # ── Cờ loại đăng ký ──────────────────────────────────────────────
    is_appointment: bool = Field(False, description="Hẹn khám")
    is_online:      bool = Field(False, description="Đăng ký online")
    is_referral:    bool = Field(False, description="Chuyển tuyến")

    # ── Đối tượng BHYT ───────────────────────────────────────────────
    subject_type: Optional[str] = Field(None, max_length=10,  description="Mã đối tượng (1=BHYT, 2=DV...)")
    subject_name: Optional[str] = Field(None, max_length=100, description="Tên đối tượng")

    # ── Thẻ BHYT ─────────────────────────────────────────────────────
    insurance_number:     Optional[str]  = Field(None, max_length=20, description="Số thẻ BHYT")
    insurance_valid_from: Optional[date] = Field(None, description="Từ ngày hạn thẻ BHYT")
    insurance_valid_to:   Optional[date] = Field(None, description="Đến ngày hạn thẻ BHYT")

    # ── ĐKKCB & giới thiệu ───────────────────────────────────────────
    initial_registration: Optional[str] = Field(None, max_length=200, description="Nơi ĐKKCB ban đầu")
    referral_note:        Optional[str] = Field(None, description="Giới thiệu")
    referral_facility:    Optional[str] = Field(None, max_length=200, description="Cơ sở giới thiệu/chuyển tuyến")

    # ── Quyền lợi đặc biệt ───────────────────────────────────────────
    high_tech_service:    bool           = Field(False, description="Được hưởng DVKT cao")
    insurance_5years:     bool           = Field(False, description="BHYT > 5 năm")
    insurance_5years_date: Optional[date] = Field(None, description="Ngày bắt đầu tính BHYT > 5 năm")

    # ── Trạng thái đặc biệt & nghèo ──────────────────────────────────
    special_status: Optional[str] = Field(None, max_length=100, description="Trạng thái đặc biệt")
    is_near_poor:   bool           = Field(False, description="Hộ cận nghèo")
    is_poor:        bool           = Field(False, description="Hộ nghèo")

    # ── Phân loại bệnh nhân ───────────────────────────────────────────
    patient_category: Optional[str] = Field(None, max_length=50, description="Người lớn / Trẻ em")
    patient_type:     Optional[str] = Field(None, max_length=10,  description="Mới / Cũ")

    # ── Lâm sàng (giữ tương thích) ───────────────────────────────────
    reason:      Optional[str] = Field(None, description="Lý do khám / triệu chứng")
    department:  Optional[str] = Field(None, max_length=100)
    doctor_name: Optional[str] = Field(None, max_length=100)
    priority:    int           = Field(0, ge=0, le=2, description="0=thường, 1=ưu tiên, 2=cấp cứu")

    # ── Liên kết & nhân viên ─────────────────────────────────────────
    queue_ticket_id:   Optional[int] = Field(None, description="ID số thứ tự")
    receptionist_name: Optional[str] = Field(None, max_length=100)
    internal_note:     Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Update
# ─────────────────────────────────────────────────────────────
class ReceptionUpdate(BaseModel):
    """Schema cập nhật tiếp đón — tất cả optional."""
    visit_time:  Optional[str] = Field(None, max_length=8)
    clinic_room: Optional[str] = Field(None, max_length=50)
    visit_number: Optional[int] = None

    is_appointment: Optional[bool] = None
    is_online:      Optional[bool] = None
    is_referral:    Optional[bool] = None

    subject_type: Optional[str] = Field(None, max_length=10)
    subject_name: Optional[str] = Field(None, max_length=100)

    insurance_number:     Optional[str]  = Field(None, max_length=20)
    insurance_valid_from: Optional[date] = None
    insurance_valid_to:   Optional[date] = None
    insurance_expiry:     Optional[date] = None

    initial_registration: Optional[str] = Field(None, max_length=200)
    referral_note:        Optional[str] = None
    referral_facility:    Optional[str] = Field(None, max_length=200)

    high_tech_service:    Optional[bool] = None
    insurance_5years:     Optional[bool] = None
    insurance_5years_date: Optional[date] = None

    special_status: Optional[str] = Field(None, max_length=100)
    is_near_poor:   Optional[bool] = None
    is_poor:        Optional[bool] = None

    patient_category: Optional[str] = Field(None, max_length=50)
    patient_type:     Optional[str] = Field(None, max_length=10)

    reason:      Optional[str] = None
    department:  Optional[str] = Field(None, max_length=100)
    doctor_name: Optional[str] = Field(None, max_length=100)
    priority:    Optional[int] = Field(None, ge=0, le=2)

    receptionist_name: Optional[str] = Field(None, max_length=100)
    internal_note:     Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Check-in
# ─────────────────────────────────────────────────────────────
class ReceptionCheckIn(BaseModel):
    """Schema check-in: PENDING → CHECKED_IN."""
    queue_ticket_id:   Optional[int] = Field(None, description="Gán số thứ tự")
    receptionist_name: Optional[str] = Field(None, max_length=100)
    internal_note:     Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Response
# ─────────────────────────────────────────────────────────────
class ReceptionResponse(BaseModel):
    """Schema trả về chi tiết đầy đủ một lần tiếp đón."""
    id:         int
    visit_date: date
    visit_time: Optional[str]  = None
    status:     ReceptionStatus

    clinic_room:  Optional[str] = None
    visit_number: Optional[int] = None

    is_appointment: bool = False
    is_online:      bool = False
    is_referral:    bool = False

    subject_type: Optional[str] = None
    subject_name: Optional[str] = None

    insurance_number:     Optional[str]  = None
    insurance_valid_from: Optional[date] = None
    insurance_valid_to:   Optional[date] = None
    insurance_expiry:     Optional[date] = None

    initial_registration: Optional[str] = None
    referral_note:        Optional[str] = None
    referral_facility:    Optional[str] = None

    high_tech_service:    bool           = False
    insurance_5years:     bool           = False
    insurance_5years_date: Optional[date] = None

    special_status: Optional[str] = None
    is_near_poor:   bool = False
    is_poor:        bool = False

    patient_category: Optional[str] = None
    patient_type:     Optional[str] = None

    reason:      Optional[str] = None
    department:  Optional[str] = None
    doctor_name: Optional[str] = None
    priority:    int = 0

    checked_in_at:     Optional[datetime] = None
    completed_at:      Optional[datetime] = None
    receptionist_name: Optional[str]      = None
    internal_note:     Optional[str]      = None

    patient_id:      int
    queue_ticket_id: Optional[int] = None

    created_at: datetime
    updated_at: datetime

    # Nested
    patient: Optional[PatientList] = None

    model_config = {"from_attributes": True}


class ReceptionList(BaseModel):
    """Schema tóm tắt cho bảng danh sách tiếp đón."""
    id:         int
    visit_date: date
    visit_time: Optional[str]    = None
    status:     ReceptionStatus
    clinic_room:  Optional[str]  = None
    visit_number: Optional[int]  = None
    department:   Optional[str]  = None
    priority:     int             = 0
    patient_type: Optional[str]  = None
    subject_name: Optional[str]  = None
    insurance_number: Optional[str] = None
    patient_id:      int
    queue_ticket_id: Optional[int] = None
    checked_in_at:   Optional[datetime] = None

    # Thông tin bệnh nhân tóm tắt
    patient: Optional[PatientList] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
# Thống kê phòng khám
# ─────────────────────────────────────────────────────────────
class ClinicRoomStat(BaseModel):
    """Thống kê số lượt khám theo phòng khám."""
    clinic_room: str
    total:  int = 0
    pending: int = 0
    bhyt:    int = 0
    service: int = 0   # Dịch vụ (không BHYT)

class ClinicRoomStatResponse(BaseModel):
    """Response bảng thống kê toàn bộ phòng khám."""
    rooms: list[ClinicRoomStat]
    total_all:    int = 0
    total_pending: int = 0
    total_bhyt:   int = 0
    total_service: int = 0
