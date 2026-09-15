"""API schemas for batch-aware drug inventory."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class BatchReceive(BaseModel):
    drug_id: int
    lot_number: str = Field(..., min_length=1, max_length=100)
    expiry_date: date
    quantity: Decimal = Field(..., gt=0)
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0)
    supplier: Optional[str] = Field(None, max_length=200)
    note: Optional[str] = None


class BatchAdjust(BaseModel):
    batch_id: int
    quantity: Decimal = Field(..., ne=0)
    reason: str = Field(..., min_length=1, max_length=500)


class BatchDispense(BaseModel):
    drug_id: int
    quantity: Decimal = Field(..., gt=0)
    source_type: str = Field(..., min_length=1, max_length=50)
    source_id: Optional[int] = None
    reference: Optional[str] = Field(None, max_length=100)
    reason: Optional[str] = Field(None, max_length=500)


class DrugBatchResponse(BaseModel):
    id: int
    drug_id: int
    lot_number: str
    expiry_date: date
    received_quantity: Decimal
    available_quantity: Decimal
    unit_cost: Decimal
    supplier: Optional[str] = None
    received_at: datetime
    active: str
    note: Optional[str] = None
    model_config = {"from_attributes": True}


class InventoryTransactionResponse(BaseModel):
    id: int
    drug_id: int
    batch_id: int
    quantity: Decimal
    transaction_type: str
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    reference: Optional[str] = None
    actor_id: Optional[int] = None
    reason: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}
