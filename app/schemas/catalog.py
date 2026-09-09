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
    drug_name:         Optional[str]     = Field(None, max_length=200)
    generic_name:      Optional[str]     = None
    active_ingredient: Optional[str]     = None
    drug_group:        Optional[str]     = None
    dosage_form:       Optional[str]     = None
    strength:          Optional[str]     = None
    unit:              Optional[str]     = None
    unit_price:        Optional[Decimal] = None
    bhyt_price:        Optional[Decimal] = None
    bhyt_ratio:        Optional[Decimal] = None
    stock_quantity:    Optional[int]     = None
    min_stock:         Optional[int]     = None
    manufacturer:      Optional[str]     = None
    country:           Optional[str]     = None
    registration_no:   Optional[str]     = None
    is_active:         Optional[bool]    = None
    is_bhyt:           Optional[bool]    = None
    note:              Optional[str]     = None


class DrugResponse(DrugBase):
    id:         int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


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
    service_name:     Optional[str]     = None
    service_group:    Optional[str]     = None
    unit:             Optional[str]     = None
    unit_price:       Optional[Decimal] = None
    bhyt_price:       Optional[Decimal] = None
    bhyt_ratio:       Optional[Decimal] = None
    result_fields:    Optional[str]     = None
    turnaround_hours: Optional[int]     = None
    department:       Optional[str]     = None
    is_active:        Optional[bool]    = None
    is_bhyt:          Optional[bool]    = None
    note:             Optional[str]     = None


class ClsServiceResponse(ClsServiceBase):
    id:         int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


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
    code:    str = Field(..., max_length=10)
    name_vi: str = Field(..., max_length=500)
    name_en: Optional[str] = Field(None, max_length=500)
    chapter: Optional[str] = Field(None, max_length=10)
    block:   Optional[str] = Field(None, max_length=20)
    is_leaf: bool = True


class Icd10BulkRequest(BaseModel):
    items: List[Icd10BulkItem]


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
