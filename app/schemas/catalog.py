"""
Pydantic schemas cho danh mục hệ thống.

Bao gồm: Drug, ClsService, Icd10, SystemConfig, AuditLog.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any
from pydantic import BaseModel, Field


# ─── Drug — Danh mục thuốc ───────────────────────────────────────────────────

class DrugBase(BaseModel):
    drug_code:         str          = Field(..., max_length=30,  description="Mã thuốc")
    drug_name:         str          = Field(..., max_length=200, description="Tên thương mại")
    generic_name:      Optional[str] = Field(None, max_length=200)
    active_ingredient: Optional[str] = Field(None, max_length=300, description="Hoạt chất")
    drug_group:        Optional[str] = Field(None, max_length=100)
    dosage_form:       Optional[str] = Field(None, max_length=100, description="Dạng bào chế")
    strength:          Optional[str] = Field(None, max_length=50,  description="Hàm lượng")
    unit:              str          = Field(..., max_length=30,  description="Đơn vị tính")
    unit_price:        Decimal      = Field(default=Decimal("0"), description="Giá bán VND")
    bhyt_price:        Optional[Decimal] = None
    bhyt_ratio:        Optional[Decimal] = Field(None, ge=0, le=1)
    stock_quantity:    int          = Field(default=0, ge=0)
    min_stock:         int          = Field(default=0, ge=0)
    manufacturer:      Optional[str] = Field(None, max_length=200)
    country:           Optional[str] = Field(None, max_length=50)
    registration_no:   Optional[str] = Field(None, max_length=50)
    is_active:         bool         = True
    is_bhyt:           bool         = False
    note:              Optional[str] = None


class DrugCreate(DrugBase):
    """Tạo mới thuốc."""
    pass


class DrugUpdate(BaseModel):
    """Cập nhật thuốc — tất cả optional."""
    drug_name:         Optional[str]     = Field(None, max_length=200, json_schema_extra={"example": "Paracetamol 500mg"})
    generic_name:      Optional[str]     = Field(None, json_schema_extra={"example": "Paracetamol"})
    active_ingredient: Optional[str]     = Field(None, json_schema_extra={"example": "Paracetamol"})
    drug_group:        Optional[str]     = Field(None, json_schema_extra={"example": "Giảm đau hạ sốt"})
    dosage_form:       Optional[str]     = Field(None, json_schema_extra={"example": "Viên nén"})
    strength:          Optional[str]     = Field(None, json_schema_extra={"example": "500mg"})
    unit:              Optional[str]     = Field(None, json_schema_extra={"example": "Hộp"})
    unit_price:        Optional[Decimal] = Field(None, json_schema_extra={"example": "25000"})
    bhyt_price:        Optional[Decimal] = Field(None, json_schema_extra={"example": "18000"})
    bhyt_ratio:        Optional[Decimal] = Field(None, json_schema_extra={"example": "0.8"})
    stock_quantity:    Optional[int]     = Field(None, json_schema_extra={"example": 100})
    min_stock:         Optional[int]     = Field(None, json_schema_extra={"example": 20})
    manufacturer:      Optional[str]     = Field(None, json_schema_extra={"example": "Công ty Dược A"})
    country:           Optional[str]     = Field(None, json_schema_extra={"example": "Việt Nam"})
    registration_no:   Optional[str]     = Field(None, json_schema_extra={"example": "VN-12345"})
    is_active:         Optional[bool]    = Field(None, json_schema_extra={"example": True})
    is_bhyt:           Optional[bool]    = Field(None, json_schema_extra={"example": True})
    note:              Optional[str]     = Field(None, json_schema_extra={"example": "Thuốc điều trị hạ sốt"})


class DrugResponse(DrugBase):
    id:         int
    created_at: datetime
    updated_at: datetime
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "drug_code": "PAR500",
                "drug_name": "Paracetamol 500mg",
                "generic_name": "Paracetamol",
                "unit": "Hộp",
                "unit_price": "25000",
                "stock_quantity": 100,
                "is_active": True,
                "is_bhyt": True,
                "created_at": "2025-02-10T09:00:00",
                "updated_at": "2025-02-10T09:05:00",
            }
        },
    }


class DrugList(BaseModel):
    """Tóm tắt dùng cho dropdown / tìm kiếm."""
    id:                int
    drug_code:         str
    drug_name:         str
    generic_name:      Optional[str] = None
    active_ingredient: Optional[str] = None
    unit:              str
    unit_price:        Decimal
    bhyt_price:        Optional[Decimal] = None
    bhyt_ratio:        Optional[Decimal] = None
    stock_quantity:    int
    is_bhyt:           bool
    is_active:         bool
    model_config = {"from_attributes": True}


# ─── ClsService — Danh mục dịch vụ CLS ──────────────────────────────────────

class ClsServiceBase(BaseModel):
    service_code:      str          = Field(..., max_length=30)
    service_name:      str          = Field(..., max_length=300)
    service_group:     Optional[str] = Field(None, max_length=50,
                                             description="lab|imaging|procedure|other")
    unit:              str          = Field(default="lần", max_length=30)
    unit_price:        Decimal      = Field(default=Decimal("0"))
    bhyt_price:        Optional[Decimal] = None
    bhyt_ratio:        Optional[Decimal] = Field(None, ge=0, le=1)
    result_fields:     Optional[str] = Field(None, description="JSON schema chỉ số kết quả")
    turnaround_hours:  Optional[int] = Field(None, ge=0)
    department:        Optional[str] = Field(None, max_length=100)
    is_active:         bool         = True
    is_bhyt:           bool         = False
    note:              Optional[str] = None


class ClsServiceCreate(ClsServiceBase):
    pass


class ClsServiceUpdate(BaseModel):
    service_name:     Optional[str]     = Field(None, json_schema_extra={"example": "Xét nghiệm công thức máu"})
    service_group:    Optional[str]     = Field(None, json_schema_extra={"example": "lab"})
    unit:             Optional[str]     = Field(None, json_schema_extra={"example": "Lần"})
    unit_price:       Optional[Decimal] = Field(None, json_schema_extra={"example": "180000"})
    bhyt_price:       Optional[Decimal] = Field(None, json_schema_extra={"example": "150000"})
    bhyt_ratio:       Optional[Decimal] = Field(None, json_schema_extra={"example": "0.8"})
    result_fields:    Optional[str]     = Field(None, json_schema_extra={"example": "[{\"name\":\"wbc\",\"label\":\"WBC\"}]"})
    turnaround_hours: Optional[int]     = Field(None, json_schema_extra={"example": 6})
    department:       Optional[str]     = Field(None, json_schema_extra={"example": "Huyết học"})
    is_active:        Optional[bool]    = Field(None, json_schema_extra={"example": True})
    is_bhyt:          Optional[bool]    = Field(None, json_schema_extra={"example": True})
    note:             Optional[str]     = Field(None, json_schema_extra={"example": "Lấy mẫu buổi sáng"})


class ClsServiceResponse(ClsServiceBase):
    id:         int
    created_at: datetime
    updated_at: datetime
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 10,
                "service_code": "CBC01",
                "service_name": "Xét nghiệm công thức máu",
                "service_group": "lab",
                "unit": "Lần",
                "unit_price": "180000",
                "is_bhyt": True,
                "created_at": "2025-02-10T09:00:00",
                "updated_at": "2025-02-10T09:10:00",
            }
        },
    }


class ClsServiceList(BaseModel):
    id:            int
    service_code:  str
    service_name:  str
    service_group: Optional[str] = None
    unit:          str
    unit_price:    Decimal
    bhyt_price:    Optional[Decimal] = None
    bhyt_ratio:    Optional[Decimal] = None
    is_bhyt:       bool
    is_active:     bool
    model_config = {"from_attributes": True}


# ─── Icd10 — Danh mục mã bệnh ───────────────────────────────────────────────

class Icd10Response(BaseModel):
    id:      int
    code:    str
    name_vi: str
    name_en: Optional[str] = None
    chapter: Optional[str] = None
    block:   Optional[str] = None
    is_leaf: bool
    model_config = {"from_attributes": True}


class Icd10BulkItem(BaseModel):
    """Dùng cho import bulk từ file."""
    code:    str = Field(..., max_length=10, json_schema_extra={"example": "J18.9"})
    name_vi: str = Field(..., max_length=500, json_schema_extra={"example": "Viêm phổi không xác định nguyên nhân"})
    name_en: Optional[str] = Field(None, max_length=500, json_schema_extra={"example": "Pneumonia, unspecified"})
    chapter: Optional[str] = Field(None, max_length=10, json_schema_extra={"example": "J"})
    block:   Optional[str] = Field(None, max_length=20, json_schema_extra={"example": "J10-J18"})
    is_leaf: bool = Field(True, json_schema_extra={"example": True})


class Icd10BulkRequest(BaseModel):
    items: List[Icd10BulkItem] = Field(..., json_schema_extra={"example": [{"code": "J18.9", "name_vi": "Viêm phổi không xác định nguyên nhân", "name_en": "Pneumonia, unspecified", "chapter": "J", "block": "J10-J18"}]})


# ─── SystemConfig — Cấu hình cơ sở ──────────────────────────────────────────

class SystemConfigUpdate(BaseModel):
    """Cập nhật giá trị một config key."""
    value: Optional[str] = None


class SystemConfigUpsert(BaseModel):
    """Tạo hoặc cập nhật config."""
    key:         str  = Field(..., max_length=100)
    value:       Optional[str] = None
    label:       str  = Field(..., max_length=200)
    group:       str  = Field(default="system", max_length=50)
    description: Optional[str] = None
    is_public:   bool = False


class SystemConfigResponse(BaseModel):
    id:          int
    key:         str
    value:       Optional[str] = None
    label:       str
    group:       str
    description: Optional[str] = None
    is_public:   bool
    updated_by:  Optional[str] = None
    updated_at:  datetime
    model_config = {"from_attributes": True}


# ─── AuditLog ────────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id:          int
    created_at:  datetime
    user_id:     Optional[int]  = None
    username:    Optional[str]  = None
    action:      str
    table_name:  Optional[str]  = None
    record_id:   Optional[int]  = None
    old_data:    Optional[str]  = None
    new_data:    Optional[str]  = None
    ip_address:  Optional[str]  = None
    description: Optional[str]  = None
    model_config = {"from_attributes": True}


class AuditLogCreate(BaseModel):
    user_id:     Optional[int]  = None
    username:    Optional[str]  = None
    action:      str            = Field(..., max_length=20)
    table_name:  Optional[str]  = Field(None, max_length=100)
    record_id:   Optional[int]  = None
    old_data:    Optional[str]  = None
    new_data:    Optional[str]  = None
    ip_address:  Optional[str]  = Field(None, max_length=45)
    description: Optional[str]  = Field(None, max_length=500)
