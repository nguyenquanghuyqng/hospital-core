"""BHYT verification and claim API schemas."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class EligibilityRequest(BaseModel):
    insurance_number: str = Field(..., min_length=5, max_length=20)


class EligibilityResponse(BaseModel):
    id: int
    patient_id: int
    reception_id: Optional[int] = None
    insurance_number: str
    status: str
    response_code: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    coverage_percent: Optional[Decimal] = None
    checked_at: datetime
    model_config = {"from_attributes": True}


class ClaimResponse(BaseModel):
    id: int
    bill_id: int
    examination_id: int
    claim_number: str
    status: str
    external_ref: Optional[str] = None
    submitted_at: Optional[datetime] = None
    accepted_amount: Optional[Decimal] = None
    rejected_amount: Optional[Decimal] = None
    correction_of_id: Optional[int] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class ReconciliationRequest(BaseModel):
    status: str = Field(..., pattern="^(accepted|rejected|partial|reconciled)$")
    accepted_amount: Decimal = Field(..., ge=0)
    rejected_amount: Decimal = Field(..., ge=0)
    external_ref: Optional[str] = Field(None, max_length=100)
    response_payload: Optional[str] = None
