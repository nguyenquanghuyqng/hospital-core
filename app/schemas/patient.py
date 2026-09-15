"""
Pydantic schemas cho bệnh nhân.

Cung cấp các schema validation cho create / update / response,
bao gồm validators cho CCCD, số điện thoại, và giới tính.
"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re


# ─────────────────────────────────────────────────────────────────────────────
# Base schema — fields dùng chung cho Create / Update
# ─────────────────────────────────────────────────────────────────────────────

class PatientBase(BaseModel):
    """
    Base schema chứa toàn bộ fields hành chính của bệnh nhân.

    Kế thừa bởi :class:`PatientCreate` và dùng làm nền cho :class:`PatientResponse`.
    Tất cả fields ngoài ``full_name`` đều là optional để hỗ trợ nhập liệu từng phần.

    Validators tích hợp:
    - :meth:`validate_cccd`: CCCD/CMND phải có đúng 9 hoặc 12 chữ số.
    - :meth:`validate_phone`: Số điện thoại Việt Nam (``+84`` hoặc ``0`` + 8–10 số).
    - :meth:`validate_gender`: Chỉ chấp nhận ``"male"`` hoặc ``"female"``.
    """

    # Thông tin cá nhân
    full_name:      str           = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Họ và tên",
        json_schema_extra={"example": "Nguyễn Văn An"},
    )
    date_of_birth:  Optional[date] = Field(None, description="Ngày sinh", json_schema_extra={"example": "1990-05-20"})
    birth_year:     Optional[int]  = Field(None, ge=1900, le=2100, description="Năm sinh", json_schema_extra={"example": 1990})
    gender:         Optional[str]  = Field(None, description="Giới tính: male / female", json_schema_extra={"example": "male"})

    # CCCD / CMND
    cccd:             Optional[str]  = Field(None, max_length=12, description="Số CCCD/CMND (9 hoặc 12 số)", json_schema_extra={"example": "012345678901"})
    cccd_issued_by:   Optional[str]  = Field(None, max_length=200, description="Nơi cấp CCCD/CMND", json_schema_extra={"example": "Cục Cảnh sát QLHC về TTXH"})
    cccd_issued_date: Optional[date] = Field(None, description="Ngày cấp CCCD/CMND", json_schema_extra={"example": "2020-05-15"})

    # Nghề nghiệp
    occupation: Optional[str] = Field(None, max_length=100, description="Nghề nghiệp", json_schema_extra={"example": "Kỹ sư phần mềm"})

    # Dân tộc (mã + tên, VD: 25 - Kinh)
    ethnicity_code: Optional[str] = Field(None, max_length=10,  description="Mã dân tộc (VD: 25)", json_schema_extra={"example": "KINH"})
    ethnicity_name: Optional[str] = Field(None, max_length=50,  description="Tên dân tộc (VD: Kinh)", json_schema_extra={"example": "Kinh"})

    # Quốc tịch (mã + tên, VD: VN - VIET NAM)
    nationality_code: Optional[str] = Field(None, max_length=10,  description="Mã quốc tịch (VD: VN)", json_schema_extra={"example": "VN"})
    nationality_name: Optional[str] = Field(None, max_length=100, description="Tên quốc tịch (VD: VIET NAM)", json_schema_extra={"example": "Việt Nam"})

    # Địa chỉ chi tiết
    address_street:        Optional[str] = Field(None, max_length=200, description="Số nhà, đường", json_schema_extra={"example": "12 Lê Lợi"})
    address_village:       Optional[str] = Field(None, max_length=100, description="Thôn/phố", json_schema_extra={"example": "Phường Bến Nghé"})
    address_ward_code:     Optional[str] = Field(None, max_length=10,  description="Mã phường/xã", json_schema_extra={"example": "01"})
    address_ward_name:     Optional[str] = Field(None, max_length=100, description="Tên phường/xã", json_schema_extra={"example": "Bến Nghé"})
    address_district_code: Optional[str] = Field(None, max_length=10,  description="Mã quận/huyện", json_schema_extra={"example": "01"})
    address_district_name: Optional[str] = Field(None, max_length=100, description="Tên quận/huyện", json_schema_extra={"example": "Quận 1"})
    address_province_code: Optional[str] = Field(None, max_length=10,  description="Mã tỉnh/TP (VD: 505)", json_schema_extra={"example": "79"})
    address_province_name: Optional[str] = Field(None, max_length=100, description="Tên tỉnh/TP (VD: Tỉnh Quảng Ngãi)", json_schema_extra={"example": "TP Hồ Chí Minh"})
    address:               Optional[str] = Field(None, description="Địa chỉ đầy đủ (tổng hợp hoặc nhập tay)", json_schema_extra={"example": "12 Lê Lợi, Phường Bến Nghé, Quận 1, TP Hồ Chí Minh"})

    # Nơi làm việc
    workplace: Optional[str] = Field(None, max_length=200, description="Nơi làm việc", json_schema_extra={"example": "Công ty TNHH ABC"})

    # Liên hệ
    phone: Optional[str] = Field(None, max_length=15, description="Số điện thoại di động", json_schema_extra={"example": "0909123456"})
    email: Optional[str] = Field(None, max_length=100, description="Email", json_schema_extra={"example": "nguyenvanan@gmail.com"})

    # Đối tượng chính sách
    policy_type: Optional[str] = Field(None, max_length=50, description="Loại đối tượng (hộ nghèo, cận nghèo...)", json_schema_extra={"example": "bhyt"})

    # Người thân / người đi cùng
    contact_name:    Optional[str] = Field(None, max_length=100, description="Họ tên người thân", json_schema_extra={"example": "Nguyễn Thị Lan"})
    contact_address: Optional[str] = Field(None, max_length=200, description="Địa chỉ người thân", json_schema_extra={"example": "34 Võ Văn Tần, Phường 6, Quận 3"})
    contact_phone:   Optional[str] = Field(None, max_length=15,  description="SĐT người thân", json_schema_extra={"example": "0987654321"})
    contact_cccd:    Optional[str] = Field(None, max_length=12,  description="CMND người thân", json_schema_extra={"example": "321098765432"})

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("cccd")
    @classmethod
    def validate_cccd(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate số CCCD/CMND.

        Loại bỏ khoảng trắng rồi kiểm tra phải có đúng 9 hoặc 12 chữ số.

        Args:
            v: Giá trị CCCD/CMND cần validate.

        Returns:
            Chuỗi CCCD đã loại bỏ khoảng trắng, hoặc ``None`` nếu không truyền.

        Raises:
            ValueError: Nếu không khớp định dạng 9 hoặc 12 chữ số.
        """
        if v is None:
            return v
        cleaned = re.sub(r"\s+", "", v)
        if not re.match(r"^\d{9}$|^\d{12}$", cleaned):
            raise ValueError("CCCD/CMND phải có 9 hoặc 12 chữ số")
        return cleaned

    @field_validator("phone", "contact_phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate số điện thoại Việt Nam.

        Loại bỏ ký tự phân cách (khoảng trắng, dấu gạch, ngoặc)
        rồi kiểm tra định dạng ``+84xxxxxxxxx`` hoặc ``0xxxxxxxxx``.

        Args:
            v: Số điện thoại cần validate (áp dụng cho ``phone`` và ``contact_phone``).

        Returns:
            Số điện thoại đã làm sạch, hoặc ``None`` nếu không truyền.

        Raises:
            ValueError: Nếu không khớp định dạng số điện thoại Việt Nam.
        """
        if v is None:
            return v
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^(\+84|0)[0-9]{8,10}$", cleaned):
            raise ValueError("Số điện thoại không hợp lệ")
        return cleaned

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate giá trị giới tính.

        Args:
            v: Giá trị giới tính cần validate.

        Returns:
            Chuỗi giới tính hợp lệ, hoặc ``None`` nếu không truyền.

        Raises:
            ValueError: Nếu giá trị không phải ``"male"`` hoặc ``"female"``.
        """
        if v is not None and v not in ("male", "female"):
            raise ValueError("Giới tính phải là: male hoặc female")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# Create / Update
# ─────────────────────────────────────────────────────────────────────────────

class PatientCreate(PatientBase):
    """
    Schema tạo mới bệnh nhân.

    Kế thừa toàn bộ fields và validators từ :class:`PatientBase`.
    ``patient_code`` được server tự sinh — không cần truyền từ client.
    """
    pass


class PatientUpdate(BaseModel):
    """
    Schema cập nhật bệnh nhân — tất cả fields đều optional.

    Chỉ các fields được truyền vào mới được cập nhật (partial update).
    Dùng ``exclude_unset=True`` khi gọi ``model_dump()`` để phân biệt
    field chưa truyền với field truyền giá trị ``None``.
    """

    full_name:      Optional[str]  = Field(None, min_length=2, max_length=100, json_schema_extra={"example": "Nguyễn Văn An"})
    date_of_birth:  Optional[date] = Field(None, json_schema_extra={"example": "1990-05-20"})
    birth_year:     Optional[int]  = Field(None, ge=1900, le=2100, json_schema_extra={"example": 1990})
    gender:         Optional[str]  = Field(None, json_schema_extra={"example": "male"})

    cccd:             Optional[str]  = Field(None, max_length=12, json_schema_extra={"example": "012345678901"})
    cccd_issued_by:   Optional[str]  = Field(None, max_length=200, json_schema_extra={"example": "Cục Cảnh sát QLHC về TTXH"})
    cccd_issued_date: Optional[date] = Field(None, json_schema_extra={"example": "2020-05-15"})

    occupation:      Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "Kỹ sư phần mềm"})
    ethnicity_code:  Optional[str] = Field(None, max_length=10, json_schema_extra={"example": "KINH"})
    ethnicity_name:  Optional[str] = Field(None, max_length=50, json_schema_extra={"example": "Kinh"})
    nationality_code: Optional[str] = Field(None, max_length=10, json_schema_extra={"example": "VN"})
    nationality_name: Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "Việt Nam"})

    address_street:        Optional[str] = Field(None, max_length=200, json_schema_extra={"example": "12 Lê Lợi"})
    address_village:       Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "Phường Bến Nghé"})
    address_ward_code:     Optional[str] = Field(None, max_length=10, json_schema_extra={"example": "01"})
    address_ward_name:     Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "Bến Nghé"})
    address_district_code: Optional[str] = Field(None, max_length=10, json_schema_extra={"example": "01"})
    address_district_name: Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "Quận 1"})
    address_province_code: Optional[str] = Field(None, max_length=10, json_schema_extra={"example": "79"})
    address_province_name: Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "TP Hồ Chí Minh"})
    address:               Optional[str] = Field(None, json_schema_extra={"example": "12 Lê Lợi, Phường Bến Nghé, Quận 1, TP Hồ Chí Minh"})

    workplace:   Optional[str] = Field(None, max_length=200, json_schema_extra={"example": "Công ty TNHH ABC"})
    phone:       Optional[str] = Field(None, max_length=15, json_schema_extra={"example": "0909123456"})
    email:       Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "nguyenvanan@gmail.com"})
    policy_type: Optional[str] = Field(None, max_length=50, json_schema_extra={"example": "bhyt"})

    contact_name:    Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "Nguyễn Thị Lan"})
    contact_address: Optional[str] = Field(None, max_length=200, json_schema_extra={"example": "34 Võ Văn Tần, Phường 6, Quận 3"})
    contact_phone:   Optional[str] = Field(None, max_length=15, json_schema_extra={"example": "0987654321"})
    contact_cccd:    Optional[str] = Field(None, max_length=12, json_schema_extra={"example": "321098765432"})


# ─────────────────────────────────────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class PatientResponse(PatientBase):
    """
    Schema response trả về toàn bộ thông tin bệnh nhân.

    Bao gồm tất cả fields từ :class:`PatientBase` cộng thêm
    các fields được server sinh ra: ``id``, ``patient_code``,
    ``created_at``, ``updated_at``.

    Config ``from_attributes=True`` cho phép tạo từ SQLAlchemy model instance.
    """

    id:           int
    patient_code: Optional[str] = None
    created_at:   datetime
    updated_at:   datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 101,
                "patient_code": "BN2025001",
                "full_name": "Nguyễn Văn An",
                "date_of_birth": "1990-05-20",
                "birth_year": 1990,
                "gender": "male",
                "cccd": "012345678901",
                "occupation": "Kỹ sư phần mềm",
                "phone": "0909123456",
                "email": "nguyenvanan@gmail.com",
                "address": "12 Lê Lợi, Phường Bến Nghé, Quận 1, TP Hồ Chí Minh",
                "created_at": "2025-02-10T09:00:00",
                "updated_at": "2025-02-10T09:30:00",
            }
        },
    }


class PatientList(BaseModel):
    """
    Schema tóm tắt bệnh nhân — dùng cho danh sách, dropdown, và nested response.

    Chỉ chứa các fields cần thiết để hiển thị trong bảng danh sách
    hoặc làm nested object trong :class:`~app.schemas.reception.ReceptionResponse`.
    """

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
