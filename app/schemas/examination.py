"""
Pydantic schemas cho Examination, Diagnosis, PrescriptionItem.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.enums import (
    ExaminationStatus, DispositionType, PaymentType,
)


# ─── Diagnosis ────────────────────────────────────────────────────────────────

class DiagnosisBase(BaseModel):
    icd_code:   Optional[str] = Field(None, max_length=20, description="Mã ICD-10")
    icd_name:   str           = Field(..., max_length=300, description="Tên bệnh/chẩn đoán")
    is_primary: bool          = Field(False, description="True = chẩn đoán chính")
    note:       Optional[str] = None
    sort_order: int           = Field(0, ge=0)


class DiagnosisCreate(DiagnosisBase):
    pass


class DiagnosisUpdate(BaseModel):
    icd_code:   Optional[str] = Field(None, max_length=20)
    icd_name:   Optional[str] = Field(None, max_length=300)
    is_primary: Optional[bool] = None
    note:       Optional[str]  = None
    sort_order: Optional[int]  = None


class DiagnosisResponse(DiagnosisBase):
    id:             int
    examination_id: int
    created_at:     datetime
    updated_at:     datetime
    model_config = {"from_attributes": True}


# ─── PrescriptionItem ─────────────────────────────────────────────────────────

class PrescriptionItemBase(BaseModel):
    item_type:  str = Field("drug", pattern="^(drug|cls)$",
                             description="drug = thuốc, cls = cận lâm sàng")
    item_code:  Optional[str]     = Field(None, max_length=50)
    item_name:  str               = Field(..., max_length=300)
    unit:       Optional[str]     = Field(None, max_length=30)
    quantity:   Decimal           = Field(Decimal("1"), gt=0)
    unit_price: Optional[Decimal] = None

    usage_instruction: Optional[str] = None
    valid_from: Optional[date]       = None
    valid_to:   Optional[date]       = None

    payment_type: PaymentType = Field(PaymentType.BHYT)

    total_amount:   Optional[Decimal] = None
    bhyt_amount:    Optional[Decimal] = None
    patient_amount: Optional[Decimal] = None

    room_name:   Optional[str] = Field(None, max_length=50)
    doctor_name: Optional[str] = Field(None, max_length=100)
    sort_order:  int           = Field(0, ge=0)


class PrescriptionItemCreate(PrescriptionItemBase):
    pass


class PrescriptionItemUpdate(BaseModel):
    item_type:  Optional[str]     = Field(None, pattern="^(drug|cls)$")
    item_code:  Optional[str]     = None
    item_name:  Optional[str]     = None
    unit:       Optional[str]     = None
    quantity:   Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    usage_instruction: Optional[str]     = None
    valid_from:        Optional[date]    = None
    valid_to:          Optional[date]    = None
    payment_type:      Optional[PaymentType] = None
    total_amount:      Optional[Decimal] = None
    bhyt_amount:       Optional[Decimal] = None
    patient_amount:    Optional[Decimal] = None
    room_name:         Optional[str]     = None
    doctor_name:       Optional[str]     = None
    sort_order:        Optional[int]     = None


class PrescriptionItemResponse(PrescriptionItemBase):
    id:             int
    examination_id: int
    created_at:     datetime
    updated_at:     datetime
    model_config = {"from_attributes": True}


# ─── Examination ──────────────────────────────────────────────────────────────

class ExaminationCreate(BaseModel):
    """Tạo phiếu khám từ reception_id — bác sĩ bắt đầu khám."""
    reception_id: int
    patient_id:   int
    doctor_id:    Optional[int] = None

    # Khung II
    exam_date:     Optional[date]     = None
    exam_start_at: Optional[datetime] = None
    subject_type:  Optional[str]      = Field(None, max_length=10)
    subject_name:  Optional[str]      = Field(None, max_length=100)
    insurance_number:     Optional[str]  = Field(None, max_length=20)
    insurance_valid_from: Optional[date] = None
    insurance_valid_to:   Optional[date] = None
    referral_from_type: Optional[str]  = Field(None, max_length=100)
    referral_from_name: Optional[str]  = Field(None, max_length=200)
    referral_diagnosis: Optional[str]  = None
    clinical_symptoms:  Optional[str]  = None

    # Khung III
    doctor_name:  Optional[str] = Field(None, max_length=100)
    nurse_name:   Optional[str] = Field(None, max_length=100)
    complications: Optional[str] = None
    disposition:  Optional[DispositionType] = None
    revisit_days:   Optional[int] = None
    revisit_result: Optional[str] = Field(None, max_length=50)
    transfer_to_facility: Optional[str] = Field(None, max_length=200)
    transfer_reason:      Optional[str] = None
    admit_ward:           Optional[str] = Field(None, max_length=100)
    admit_priority: bool = False
    is_near_poor:   bool = False
    is_poor:        bool = False
    flag_priority:  bool = False

    # Chẩn đoán và kê đơn có thể tạo cùng lúc
    diagnoses:          List[DiagnosisCreate]      = []
    prescription_items: List[PrescriptionItemCreate] = []


class ExaminationUpdate(BaseModel):
    """Cập nhật phiếu khám — tất cả optional."""
    status: Optional[ExaminationStatus] = None

    exam_start_at: Optional[datetime] = None
    exam_end_at:   Optional[datetime] = None
    exam_end_date: Optional[date]     = None
    subject_type:  Optional[str] = None
    subject_name:  Optional[str] = None
    insurance_number:     Optional[str]  = None
    insurance_valid_from: Optional[date] = None
    insurance_valid_to:   Optional[date] = None
    referral_from_type: Optional[str] = None
    referral_from_name: Optional[str] = None
    referral_diagnosis: Optional[str] = None
    clinical_symptoms:  Optional[str] = None

    doctor_name:  Optional[str] = None
    nurse_name:   Optional[str] = None
    complications: Optional[str] = None
    disposition:  Optional[DispositionType] = None
    revisit_days:   Optional[int] = None
    revisit_result: Optional[str] = None
    transfer_to_facility: Optional[str] = None
    transfer_reason:      Optional[str] = None
    admit_ward:           Optional[str] = None
    admit_priority: Optional[bool] = None
    is_near_poor:   Optional[bool] = None
    is_poor:        Optional[bool] = None
    flag_priority:  Optional[bool] = None

    # Đồng bộ toàn bộ diagnoses/items khi lưu
    diagnoses:          Optional[List[DiagnosisCreate]]      = None
    prescription_items: Optional[List[PrescriptionItemCreate]] = None


class ExaminationResponse(BaseModel):
    """Chi tiết đầy đủ phiếu khám."""
    id:           int
    reception_id: int
    patient_id:   int
    doctor_id:    Optional[int] = None
    status:       ExaminationStatus

    exam_date:     date
    exam_start_at: Optional[datetime] = None
    exam_end_at:   Optional[datetime] = None
    exam_end_date: Optional[date]     = None
    subject_type:  Optional[str] = None
    subject_name:  Optional[str] = None
    insurance_number:     Optional[str]  = None
    insurance_valid_from: Optional[date] = None
    insurance_valid_to:   Optional[date] = None
    referral_from_type: Optional[str] = None
    referral_from_name: Optional[str] = None
    referral_diagnosis: Optional[str] = None
    clinical_symptoms:  Optional[str] = None

    doctor_name:  Optional[str] = None
    nurse_name:   Optional[str] = None
    complications: Optional[str] = None
    disposition:  Optional[DispositionType] = None
    revisit_days:   Optional[int]  = None
    revisit_result: Optional[str]  = None
    transfer_to_facility: Optional[str] = None
    transfer_reason:      Optional[str] = None
    admit_ward:           Optional[str] = None
    admit_priority: bool = False
    is_near_poor:   bool = False
    is_poor:        bool = False
    flag_priority:  bool = False

    diagnoses:          List[DiagnosisResponse]      = []
    prescription_items: List[PrescriptionItemResponse] = []

    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ExaminationList(BaseModel):
    """Tóm tắt cho lịch sử khám."""
    id:           int
    reception_id: int
    status:       ExaminationStatus
    exam_date:    date
    doctor_name:  Optional[str] = None
    disposition:  Optional[DispositionType] = None
    created_at:   datetime
    model_config = {"from_attributes": True}


# ─── Cost summary ─────────────────────────────────────────────────────────────

class CostSummary(BaseModel):
    """Tổng hợp chi phí real-time."""
    drug_total:    Decimal = Decimal("0")
    cls_total:     Decimal = Decimal("0")
    grand_total:   Decimal = Decimal("0")
    bhyt_pays:     Decimal = Decimal("0")
    patient_pays:  Decimal = Decimal("0")
