"""
Pydantic schemas cho kết quả CLS (cận lâm sàng).

Schemas::

    ClsResultValueCreate / ClsResultValueResponse
    ClsResultCreate / ClsResultUpdate / ClsResultResponse
    DrugInteractionCheck / DrugInteractionResponse
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl

from app.models.enums import ClsResultStatus


# ─── ClsResultValue ──────────────────────────────────────────────────────────

class ClsResultValueBase(BaseModel):
    indicator_name: str           = Field(..., max_length=100, description="Tên chỉ số (VD: HGB)")
    indicator_code: Optional[str] = Field(None, max_length=50)
    value_text:     Optional[str] = Field(None, max_length=200, description="Giá trị text")
    value_numeric:  Optional[Decimal] = None
    unit:           Optional[str] = Field(None, max_length=50)
    ref_min:        Optional[Decimal] = None
    ref_max:        Optional[Decimal] = None
    ref_text:       Optional[str] = Field(None, max_length=100)
    is_abnormal:    bool = False
    sort_order:     int  = 0


class ClsResultValueCreate(ClsResultValueBase):
    pass


class ClsResultValueResponse(ClsResultValueBase):
    id:            int
    cls_result_id: int
    model_config = {"from_attributes": True}


# ─── ClsResult ───────────────────────────────────────────────────────────────

class ClsResultUpdate(BaseModel):
    """Thu ngân / kỹ thuật viên điền kết quả."""
    status:         Optional[ClsResultStatus] = None
    performed_at:   Optional[datetime]        = None
    result_at:      Optional[datetime]        = None
    performed_by:   Optional[str]             = Field(None, max_length=100)
    verified_by:    Optional[str]             = Field(None, max_length=100)
    result_summary: Optional[str]             = None
    result_note:    Optional[str]             = None
    result_file_url: Optional[str]            = Field(None, max_length=500)
    is_abnormal:    Optional[bool]            = None
    values:         Optional[List[ClsResultValueCreate]] = None


class ClsResultResponse(BaseModel):
    id:                  int
    prescription_item_id: int
    examination_id:      int
    patient_id:          int
    service_code:        Optional[str] = None
    service_name:        str
    department:          Optional[str] = None
    status:              ClsResultStatus
    performed_at:        Optional[datetime] = None
    result_at:           Optional[datetime] = None
    performed_by:        Optional[str] = None
    verified_by:         Optional[str] = None
    result_summary:      Optional[str] = None
    result_note:         Optional[str] = None
    result_file_url:     Optional[str] = None
    is_abnormal:         bool = False
    values:              List[ClsResultValueResponse] = []
    created_at:          datetime
    updated_at:          datetime
    model_config = {"from_attributes": True}


class ClsResultListItem(BaseModel):
    """Tóm tắt cho danh sách — không load values."""
    id:            int
    prescription_item_id: int
    examination_id: int
    service_name:  str
    status:        ClsResultStatus
    is_abnormal:   bool
    result_at:     Optional[datetime] = None
    performed_by:  Optional[str] = None
    created_at:    datetime
    model_config = {"from_attributes": True}


# ─── Drug Interaction ─────────────────────────────────────────────────────────

class DrugInteractionCheck(BaseModel):
    """Request check tương tác thuốc."""
    drug_codes: List[str] = Field(..., min_length=2,
                                  description="Danh sách mã thuốc cần kiểm tra (>=2)")


class DrugWarning(BaseModel):
    """Một cảnh báo tương tác / trùng hoạt chất."""
    warning_type:    str = Field(..., description="duplicate_ingredient | known_interaction")
    severity:        str = Field(..., description="info | warning | danger")
    drug_a_code:     str
    drug_a_name:     str
    drug_b_code:     str
    drug_b_name:     str
    ingredient:      Optional[str] = None
    message:         str


class DrugInteractionResponse(BaseModel):
    """Response kiểm tra tương tác thuốc."""
    has_warnings: bool
    warnings:     List[DrugWarning] = []
