"""
Pydantic schemas cho phiếu khám bệnh, chẩn đoán, và kê đơn / chỉ định CLS.

Cấu trúc schemas::

    DiagnosisBase → DiagnosisCreate / DiagnosisUpdate / DiagnosisResponse
    PrescriptionItemBase → PrescriptionItemCreate / PrescriptionItemUpdate / PrescriptionItemResponse
    ExaminationCreate / ExaminationUpdate / ExaminationResponse / ExaminationList
    CostSummary
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
    """
    Base schema chứa các fields chung cho chẩn đoán ICD-10.

    Attributes:
        icd_code: Mã bệnh ICD-10 (tuỳ chọn, VD: ``"J18.9"``).
        icd_name: Tên bệnh / chẩn đoán bằng tiếng Việt (bắt buộc).
        is_primary: ``True`` = chẩn đoán chính; ``False`` = chẩn đoán kèm theo.
        note: Ghi chú bổ sung (tuỳ chọn).
        sort_order: Thứ tự hiển thị trong phiếu (bắt đầu từ 0).
    """

    icd_code:   Optional[str] = Field(None, max_length=20, description="Mã ICD-10", json_schema_extra={"example": "J18.9"})
    icd_name:   str           = Field(..., max_length=300, description="Tên bệnh/chẩn đoán", json_schema_extra={"example": "Viêm phổi không xác định nguyên nhân"})
    is_primary: bool          = Field(False, description="True = chẩn đoán chính", json_schema_extra={"example": True})
    note:       Optional[str] = Field(None, json_schema_extra={"example": "Khởi phát từ 3 ngày trước"})
    sort_order: int           = Field(0, ge=0, json_schema_extra={"example": 1})


class DiagnosisCreate(DiagnosisBase):
    """
    Schema tạo mới chẩn đoán — kế thừa toàn bộ :class:`DiagnosisBase`.

    ``examination_id`` và ``sort_order`` được CRUD layer tự gán.
    """
    pass


class DiagnosisUpdate(BaseModel):
    """
    Schema cập nhật chẩn đoán — tất cả fields optional (partial update).
    """

    icd_code:   Optional[str] = Field(None, max_length=20)
    icd_name:   Optional[str] = Field(None, max_length=300)
    is_primary: Optional[bool] = None
    note:       Optional[str]  = None
    sort_order: Optional[int]  = None


class DiagnosisResponse(DiagnosisBase):
    """
    Schema response chi tiết một chẩn đoán, kèm metadata từ database.

    Attributes:
        id: ID chẩn đoán.
        examination_id: ID phiếu khám chứa chẩn đoán này.
        created_at: Thời điểm tạo.
        updated_at: Thời điểm cập nhật lần cuối.
    """

    id:             int
    examination_id: int
    created_at:     datetime
    updated_at:     datetime
    model_config = {"from_attributes": True}


# ─── PrescriptionItem ─────────────────────────────────────────────────────────

class PrescriptionItemBase(BaseModel):
    """
    Base schema chứa các fields chung cho dòng kê đơn / chỉ định CLS.

    Phân biệt bởi ``item_type``:
    - ``"drug"`` — thuốc kê đơn (có hướng dẫn sử dụng và ngày hiệu lực).
    - ``"cls"``  — chỉ định cận lâm sàng (xét nghiệm, chụp chiếu…).

    Attributes:
        item_type: Loại dòng — ``"drug"`` hoặc ``"cls"``.
        item_code: Mã thuốc / dịch vụ trong danh mục (tuỳ chọn).
        item_name: Tên thuốc / dịch vụ (bắt buộc).
        unit: Đơn vị tính (viên, ống, lần…).
        quantity: Số lượng (> 0, mặc định 1).
        unit_price: Đơn giá (tuỳ chọn).
        usage_instruction: Cách dùng — chỉ áp dụng cho thuốc.
        valid_from / valid_to: Thời gian hiệu lực đơn thuốc.
        payment_type: Loại chi trả — xem :class:`~app.models.enums.PaymentType`.
        total_amount: Thành tiền (tự tính nếu để trống).
        bhyt_amount: Số tiền BHYT chi trả.
        patient_amount: Số tiền bệnh nhân cùng chi trả (CCT).
    """

    item_type:  str = Field("drug", pattern="^(drug|cls)$",
                             description="drug = thuốc, cls = cận lâm sàng", json_schema_extra={"example": "drug"})
    item_code:  Optional[str]     = Field(None, max_length=50, json_schema_extra={"example": "PAR500"})
    item_name:  str               = Field(..., max_length=300, json_schema_extra={"example": "Paracetamol 500mg"})
    unit:       Optional[str]     = Field(None, max_length=30, json_schema_extra={"example": "viên"})
    quantity:   Decimal           = Field(Decimal("1"), gt=0, json_schema_extra={"example": "10"})
    unit_price: Optional[Decimal] = Field(None, json_schema_extra={"example": "2500"})

    usage_instruction: Optional[str] = Field(None, json_schema_extra={"example": "Uống 1 viên sau ăn sáng và tối"})
    valid_from: Optional[date]       = Field(None, json_schema_extra={"example": "2025-02-10"})
    valid_to:   Optional[date]       = Field(None, json_schema_extra={"example": "2025-02-17"})

    payment_type: PaymentType = Field(PaymentType.BHYT, json_schema_extra={"example": "bhyt"})

    total_amount:   Optional[Decimal] = Field(None, json_schema_extra={"example": "25000"})
    bhyt_amount:    Optional[Decimal] = Field(None, json_schema_extra={"example": "20000"})
    patient_amount: Optional[Decimal] = Field(None, json_schema_extra={"example": "5000"})

    room_name:   Optional[str] = Field(None, max_length=50, json_schema_extra={"example": "Phòng thuốc"})
    doctor_name: Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "BS. Trần Minh Đức"})
    sort_order:  int           = Field(0, ge=0, json_schema_extra={"example": 1})


class PrescriptionItemCreate(PrescriptionItemBase):
    """
    Schema tạo mới dòng kê đơn / chỉ định CLS — kế thừa :class:`PrescriptionItemBase`.

    ``examination_id``, ``sort_order``, và ``total_amount`` (nếu chưa có)
    được CRUD layer tự gán.
    """
    pass


class PrescriptionItemUpdate(BaseModel):
    """
    Schema cập nhật dòng kê đơn — tất cả fields optional (partial update).
    """

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
    """
    Schema response chi tiết một dòng kê đơn / CLS, kèm metadata.

    Attributes:
        id: ID dòng kê đơn.
        examination_id: ID phiếu khám chứa dòng này.
        created_at: Thời điểm tạo.
        updated_at: Thời điểm cập nhật lần cuối.
    """

    id:             int
    examination_id: int
    created_at:     datetime
    updated_at:     datetime
    model_config = {"from_attributes": True}


# ─── Examination ──────────────────────────────────────────────────────────────

class ExaminationCreate(BaseModel):
    """
    Schema tạo phiếu khám mới — bác sĩ bắt đầu khám bệnh nhân.

    Yêu cầu ``reception_id``. ``patient_id``, ``doctor_id`` và
    ``doctor_name`` được endpoint tự điền từ reception / user đang đăng nhập
    nếu không truyền vào.

    Chẩn đoán (``diagnoses``) và kê đơn (``prescription_items``) có thể
    được tạo đồng thời với phiếu khám.

    Attributes:
        reception_id: ID lượt tiếp đón đã CHECKED_IN (bắt buộc).
        patient_id: ID bệnh nhân (tự điền từ reception nếu để trống).
        doctor_id: ID bác sĩ (tự điền từ current_user nếu để trống).
        diagnoses: Danh sách chẩn đoán tạo cùng lúc (mặc định rỗng).
        prescription_items: Danh sách kê đơn / CLS tạo cùng lúc (mặc định rỗng).
    """

    reception_id: int = Field(..., json_schema_extra={"example": 42})
    patient_id:   Optional[int] = Field(None, json_schema_extra={"example": 101})
    doctor_id:    Optional[int] = Field(None, json_schema_extra={"example": 8})

    # Khung II — Thông tin vào
    exam_date:     Optional[date]     = Field(None, json_schema_extra={"example": "2025-02-10"})
    exam_start_at: Optional[datetime] = Field(None, json_schema_extra={"example": "2025-02-10T08:40:00"})
    subject_type:  Optional[str]      = Field(None, max_length=10, json_schema_extra={"example": "1"})
    subject_name:  Optional[str]      = Field(None, max_length=100, json_schema_extra={"example": "Bảo hiểm y tế"})
    insurance_number:     Optional[str]  = Field(None, max_length=20, json_schema_extra={"example": "KH12345678"})
    insurance_valid_from: Optional[date] = Field(None, json_schema_extra={"example": "2025-01-01"})
    insurance_valid_to:   Optional[date] = Field(None, json_schema_extra={"example": "2025-12-31"})
    referral_from_type: Optional[str]  = Field(None, max_length=100, json_schema_extra={"example": "Tuyến dưới"})
    referral_from_name: Optional[str]  = Field(None, max_length=200, json_schema_extra={"example": "Trạm Y tế xã Long Hòa"})
    referral_diagnosis: Optional[str]  = Field(None, json_schema_extra={"example": "Sốt, ho 3 ngày"})
    clinical_symptoms:  Optional[str]  = Field(None, json_schema_extra={"example": "Sốt 38.5°C, ho khan, mệt mỏi"})

    # Khung III — Thông tin khám
    doctor_name:   Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "BS. Trần Minh Đức"})
    nurse_name:    Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "ĐD. Nguyễn Thị Hoa"})
    complications: Optional[str] = Field(None, json_schema_extra={"example": "Không có biến chứng"})
    disposition:   Optional[DispositionType] = Field(None, json_schema_extra={"example": "treat"})
    revisit_days:         Optional[int] = Field(None, json_schema_extra={"example": 7})
    revisit_result:       Optional[str] = Field(None, max_length=50, json_schema_extra={"example": "Tái khám sau 1 tuần"})
    transfer_to_facility: Optional[str] = Field(None, max_length=200, json_schema_extra={"example": "Bệnh viện đa khoa tỉnh"})
    transfer_reason:      Optional[str] = Field(None, json_schema_extra={"example": "Cần chẩn đoán chuyên khoa"})
    admit_ward:           Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "Khoa Nội"})
    admit_priority: bool = Field(False, json_schema_extra={"example": False})
    is_near_poor:   bool = Field(False, json_schema_extra={"example": False})
    is_poor:        bool = Field(False, json_schema_extra={"example": False})
    flag_priority:  bool = Field(False, json_schema_extra={"example": False})

    # Chẩn đoán và kê đơn tạo cùng lúc
    diagnoses:          List[DiagnosisCreate]        = Field(default_factory=list, json_schema_extra={"example": [{"icd_code": "J18.9", "icd_name": "Viêm phổi không xác định nguyên nhân", "is_primary": True}]})
    prescription_items: List[PrescriptionItemCreate] = Field(default_factory=list, json_schema_extra={"example": [{"item_type": "drug", "item_name": "Paracetamol 500mg", "quantity": "10", "unit": "viên"}]})


class ExaminationUpdate(BaseModel):
    """
    Schema cập nhật phiếu khám — tất cả fields optional (partial update).

    Nếu ``diagnoses`` hoặc ``prescription_items`` được truyền vào,
    CRUD layer sẽ **thay thế toàn bộ** collection hiện có (replace-all).
    Nếu để ``None`` (không truyền), collection hiện có giữ nguyên.
    """

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

    doctor_name:   Optional[str] = None
    nurse_name:    Optional[str] = None
    complications: Optional[str] = None
    disposition:   Optional[DispositionType] = None
    revisit_days:         Optional[int]  = None
    revisit_result:       Optional[str]  = None
    transfer_to_facility: Optional[str]  = None
    transfer_reason:      Optional[str]  = None
    admit_ward:           Optional[str]  = None
    admit_priority: Optional[bool] = None
    is_near_poor:   Optional[bool] = None
    is_poor:        Optional[bool] = None
    flag_priority:  Optional[bool] = None

    # None = giữ nguyên collection hiện có; list = thay thế toàn bộ
    diagnoses:          Optional[List[DiagnosisCreate]]        = None
    prescription_items: Optional[List[PrescriptionItemCreate]] = None


class ExaminationResponse(BaseModel):
    """
    Schema response chi tiết đầy đủ phiếu khám, kèm collection con.

    Bao gồm tất cả thông tin lâm sàng, danh sách chẩn đoán (``diagnoses``),
    và danh sách kê đơn / CLS (``prescription_items``).

    Config ``from_attributes=True`` cho phép tạo từ SQLAlchemy model instance
    đã eager-load các collection.
    """

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

    doctor_name:   Optional[str] = None
    nurse_name:    Optional[str] = None
    complications: Optional[str] = None
    disposition:   Optional[DispositionType] = None
    revisit_days:         Optional[int]  = None
    revisit_result:       Optional[str]  = None
    transfer_to_facility: Optional[str]  = None
    transfer_reason:      Optional[str]  = None
    admit_ward:           Optional[str]  = None
    admit_priority: bool = False
    is_near_poor:   bool = False
    is_poor:        bool = False
    flag_priority:  bool = False

    diagnoses:          List[DiagnosisResponse]          = []
    prescription_items: List[PrescriptionItemResponse]   = []

    created_at: datetime
    updated_at: datetime
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 12,
                "reception_id": 42,
                "patient_id": 101,
                "doctor_id": 8,
                "status": "draft",
                "exam_date": "2025-02-10",
                "subject_type": "1",
                "subject_name": "Bảo hiểm y tế",
                "insurance_number": "KH12345678",
                "doctor_name": "BS. Trần Minh Đức",
                "clinical_symptoms": "Sốt 38.5°C, ho khan, mệt mỏi",
                "diagnoses": [{"id": 1, "examination_id": 12, "icd_code": "J18.9", "icd_name": "Viêm phổi không xác định nguyên nhân", "is_primary": True}],
                "prescription_items": [{"id": 1, "examination_id": 12, "item_type": "drug", "item_name": "Paracetamol 500mg", "quantity": "10", "unit": "viên"}],
                "created_at": "2025-02-10T08:45:00",
                "updated_at": "2025-02-10T09:00:00",
            }
        },
    }


class ExaminationList(BaseModel):
    """
    Schema tóm tắt phiếu khám — dùng cho danh sách lịch sử khám.

    Chỉ chứa các fields cần thiết để hiển thị trong bảng lịch sử:
    ngày khám, trạng thái, bác sĩ, hướng xử trí.
    """

    id:           int
    reception_id: int
    status:       ExaminationStatus
    exam_date:    date
    doctor_name:  Optional[str] = None
    disposition:  Optional[DispositionType] = None
    created_at:   datetime
    model_config = {"from_attributes": True}


# ─── Cost Summary ─────────────────────────────────────────────────────────────

class CostSummary(BaseModel):
    """
    Tổng hợp chi phí real-time của một phiếu khám.

    Được tính từ toàn bộ :class:`~app.models.examination.PrescriptionItem`
    của phiếu bởi hàm :func:`~app.crud.examination._calc_cost`.

    Attributes:
        drug_total: Tổng tiền thuốc.
        cls_total: Tổng tiền dịch vụ CLS.
        grand_total: Tổng cộng (drug + cls).
        bhyt_pays: Phần BHYT chi trả.
        patient_pays: Phần bệnh nhân cùng chi trả (CCT).
    """

    drug_total:   Decimal = Decimal("0")
    cls_total:    Decimal = Decimal("0")
    grand_total:  Decimal = Decimal("0")
    bhyt_pays:    Decimal = Decimal("0")
    patient_pays: Decimal = Decimal("0")
