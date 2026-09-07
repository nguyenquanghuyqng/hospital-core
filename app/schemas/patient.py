from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re


# ─────────────────────────────────────────────────────────────
# I. HÀNH CHÍNH — Base fields (dùng chung cho Create / Update)
# ─────────────────────────────────────────────────────────────
class PatientBase(BaseModel):
    # Thông tin cá nhân
    full_name:      str           = Field(..., min_length=2, max_length=100, description="Họ và tên")
    date_of_birth:  Optional[date] = Field(None, description="Ngày sinh")
    birth_year:     Optional[int]  = Field(None, ge=1900, le=2100, description="Năm sinh")
    gender:         Optional[str]  = Field(None, description="Giới tính: male / female")

    # CCCD / CMND
    cccd:             Optional[str]  = Field(None, max_length=12, description="Số CCCD/CMND (9 hoặc 12 số)")
    cccd_issued_by:   Optional[str]  = Field(None, max_length=200, description="Nơi cấp CCCD/CMND")
    cccd_issued_date: Optional[date] = Field(None, description="Ngày cấp CCCD/CMND")

    # Nghề nghiệp
    occupation: Optional[str] = Field(None, max_length=100, description="Nghề nghiệp")

    # Dân tộc (mã + tên, VD: 25 - Kinh)
    ethnicity_code: Optional[str] = Field(None, max_length=10,  description="Mã dân tộc (VD: 25)")
    ethnicity_name: Optional[str] = Field(None, max_length=50,  description="Tên dân tộc (VD: Kinh)")

    # Quốc tịch (mã + tên, VD: VN - VIET NAM)
    nationality_code: Optional[str] = Field(None, max_length=10,  description="Mã quốc tịch (VD: VN)")
    nationality_name: Optional[str] = Field(None, max_length=100, description="Tên quốc tịch (VD: VIET NAM)")

    # Địa chỉ chi tiết
    address_street:        Optional[str] = Field(None, max_length=200, description="Số nhà, đường")
    address_village:       Optional[str] = Field(None, max_length=100, description="Thôn/phố")
    address_ward_code:     Optional[str] = Field(None, max_length=10,  description="Mã phường/xã")
    address_ward_name:     Optional[str] = Field(None, max_length=100, description="Tên phường/xã")
    address_district_code: Optional[str] = Field(None, max_length=10,  description="Mã quận/huyện")
    address_district_name: Optional[str] = Field(None, max_length=100, description="Tên quận/huyện")
    address_province_code: Optional[str] = Field(None, max_length=10,  description="Mã tỉnh/TP (VD: 505)")
    address_province_name: Optional[str] = Field(None, max_length=100, description="Tên tỉnh/TP (VD: Tỉnh Quảng Ngãi)")
    address:               Optional[str] = Field(None, description="Địa chỉ đầy đủ (tổng hợp hoặc nhập tay)")

    # Nơi làm việc
    workplace: Optional[str] = Field(None, max_length=200, description="Nơi làm việc")

    # Liên hệ
    phone: Optional[str] = Field(None, max_length=15, description="Số điện thoại di động")
    email: Optional[str] = Field(None, max_length=100, description="Email")

    # Đối tượng chính sách
    policy_type: Optional[str] = Field(None, max_length=50, description="Loại đối tượng (hộ nghèo, cận nghèo...)")

    # Người thân / người đi cùng
    contact_name:    Optional[str] = Field(None, max_length=100, description="Họ tên người thân")
    contact_address: Optional[str] = Field(None, max_length=200, description="Địa chỉ người thân")
    contact_phone:   Optional[str] = Field(None, max_length=15,  description="SĐT người thân")
    contact_cccd:    Optional[str] = Field(None, max_length=12,  description="CMND người thân")

    # ── Validators ──────────────────────────────────────────────────
    @field_validator("cccd")
    @classmethod
    def validate_cccd(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = re.sub(r"\s+", "", v)
        if not re.match(r"^\d{9}$|^\d{12}$", cleaned):
            raise ValueError("CCCD/CMND phải có 9 hoặc 12 chữ số")
        return cleaned

    @field_validator("phone", "contact_phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^(\+84|0)[0-9]{8,10}$", cleaned):
            raise ValueError("Số điện thoại không hợp lệ")
        return cleaned

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("male", "female"):
            raise ValueError("Giới tính phải là: male hoặc female")
        return v


# ─────────────────────────────────────────────────────────────
# Create / Update
# ─────────────────────────────────────────────────────────────
class PatientCreate(PatientBase):
    """Schema tạo mới bệnh nhân — patient_code tự sinh ở server."""
    pass


class PatientUpdate(BaseModel):
    """Schema cập nhật bệnh nhân — tất cả optional."""
    full_name:      Optional[str]  = Field(None, min_length=2, max_length=100)
    date_of_birth:  Optional[date] = None
    birth_year:     Optional[int]  = Field(None, ge=1900, le=2100)
    gender:         Optional[str]  = None

    cccd:             Optional[str]  = Field(None, max_length=12)
    cccd_issued_by:   Optional[str]  = Field(None, max_length=200)
    cccd_issued_date: Optional[date] = None

    occupation:      Optional[str] = Field(None, max_length=100)
    ethnicity_code:  Optional[str] = Field(None, max_length=10)
    ethnicity_name:  Optional[str] = Field(None, max_length=50)
    nationality_code: Optional[str] = Field(None, max_length=10)
    nationality_name: Optional[str] = Field(None, max_length=100)

    address_street:        Optional[str] = Field(None, max_length=200)
    address_village:       Optional[str] = Field(None, max_length=100)
    address_ward_code:     Optional[str] = Field(None, max_length=10)
    address_ward_name:     Optional[str] = Field(None, max_length=100)
    address_district_code: Optional[str] = Field(None, max_length=10)
    address_district_name: Optional[str] = Field(None, max_length=100)
    address_province_code: Optional[str] = Field(None, max_length=10)
    address_province_name: Optional[str] = Field(None, max_length=100)
    address:               Optional[str] = None

    workplace:   Optional[str] = Field(None, max_length=200)
    phone:       Optional[str] = Field(None, max_length=15)
    email:       Optional[str] = Field(None, max_length=100)
    policy_type: Optional[str] = Field(None, max_length=50)

    contact_name:    Optional[str] = Field(None, max_length=100)
    contact_address: Optional[str] = Field(None, max_length=200)
    contact_phone:   Optional[str] = Field(None, max_length=15)
    contact_cccd:    Optional[str] = Field(None, max_length=12)


# ─────────────────────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────────────────────
class PatientResponse(PatientBase):
    """Schema trả về toàn bộ thông tin bệnh nhân."""
    id:           int
    patient_code: Optional[str] = None
    created_at:   datetime
    updated_at:   datetime

    model_config = {"from_attributes": True}


class PatientList(BaseModel):
    """Schema tóm tắt cho danh sách / dropdown."""
    id:           int
    patient_code: Optional[str] = None
    full_name:    str
    cccd:         Optional[str] = None
    date_of_birth: Optional[date] = None
    birth_year:   Optional[int] = None
    gender:       Optional[str] = None
    phone:        Optional[str] = None
    address_province_name: Optional[str] = None

    model_config = {"from_attributes": True}
