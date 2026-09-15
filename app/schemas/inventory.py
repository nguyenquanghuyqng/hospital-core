"""API schemas for batch-aware drug inventory."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class BatchReceive(BaseModel):
    drug_id: int = Field(..., json_schema_extra={"example": 101})
    lot_number: str = Field(..., min_length=1, max_length=100, json_schema_extra={"example": "LOT-2025-001"})
    expiry_date: date = Field(..., json_schema_extra={"example": "2026-12-31"})
    quantity: Decimal = Field(..., gt=0, json_schema_extra={"example": "1200"})
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0, json_schema_extra={"example": "35000"})
    supplier: Optional[str] = Field(None, max_length=200, json_schema_extra={"example": "Công ty Dược phẩm A"})
    note: Optional[str] = Field(None, json_schema_extra={"example": "Nhập hàng theo hợp đồng tháng 2"})


class BatchAdjust(BaseModel):
    batch_id: int = Field(..., json_schema_extra={"example": 15})
    quantity: Decimal = Field(..., ne=0, json_schema_extra={"example": "-30"})
    reason: str = Field(..., min_length=1, max_length=500, json_schema_extra={"example": "Kiểm kê đầu tháng"})


class BatchDispense(BaseModel):
    drug_id: int = Field(..., json_schema_extra={"example": 101})
    quantity: Decimal = Field(..., gt=0, json_schema_extra={"example": "10"})
    source_type: str = Field(..., min_length=1, max_length=50, json_schema_extra={"example": "examination"})
    source_id: Optional[int] = Field(None, json_schema_extra={"example": 88})
    reference: Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "HD-2025-015"})
    reason: Optional[str] = Field(None, max_length=500, json_schema_extra={"example": "Xuất cho bệnh nhân theo đơn thuốc"})


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
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 15,
                "drug_id": 101,
                "lot_number": "LOT-2025-001",
                "expiry_date": "2026-12-31",
                "received_quantity": "1200",
                "available_quantity": "1150",
                "unit_cost": "35000",
                "supplier": "Công ty Dược phẩm A",
                "received_at": "2025-02-10T09:00:00",
                "active": "active",
                "note": "Nhập hàng theo hợp đồng tháng 2",
            }
        },
    }


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
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 291,
                "drug_id": 101,
                "batch_id": 15,
                "quantity": "10",
                "transaction_type": "dispense",
                "source_type": "examination",
                "source_id": 88,
                "reference": "HD-2025-015",
                "actor_id": 7,
                "reason": "Xuất cho bệnh nhân theo đơn thuốc",
                "created_at": "2025-02-10T10:40:00",
            }
        },
    }
