"""BHYT verification and claim API schemas."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class EligibilityRequest(BaseModel):
    insurance_number: str = Field(
        ...,
        min_length=5,
        max_length=20,
        json_schema_extra={"example": "0123456789"},
    )


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
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 12,
                "patient_id": 102,
                "reception_id": 45,
                "insurance_number": "0123456789",
                "status": "eligible",
                "response_code": "00",
                "valid_from": "2025-01-01",
                "valid_to": "2025-12-31",
                "coverage_percent": "80",
                "checked_at": "2025-02-10T09:15:00",
            }
        },
    }


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
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 77,
                "bill_id": 801,
                "examination_id": 110,
                "claim_number": "BHYT-2025-00077",
                "status": "submitted",
                "external_ref": "BHYT-REF-2025-001",
                "submitted_at": "2025-02-10T10:05:00",
                "accepted_amount": "5400000",
                "rejected_amount": "0",
                "correction_of_id": None,
                "created_at": "2025-02-10T10:00:00",
            }
        },
    }


class ReconciliationRequest(BaseModel):
    status: str = Field(..., pattern="^(accepted|rejected|partial|reconciled)$", json_schema_extra={"example": "accepted"})
    accepted_amount: Decimal = Field(..., ge=0, json_schema_extra={"example": "5400000"})
    rejected_amount: Decimal = Field(..., ge=0, json_schema_extra={"example": "0"})
    external_ref: Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "BHYT-REF-2025-001"})
    response_payload: Optional[str] = Field(None, json_schema_extra={"example": "{\"result\":\"accepted\"}"})
