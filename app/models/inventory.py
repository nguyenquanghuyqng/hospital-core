"""Batch-aware inventory models for drugs and immutable stock movements."""
from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func

from app.db.base import Base


class DrugBatch(Base):
    __tablename__ = "drug_batches"

    id = Column(Integer, primary_key=True, index=True)
    drug_id = Column(Integer, ForeignKey("drugs.id", ondelete="RESTRICT"), nullable=False, index=True)
    lot_number = Column(String(100), nullable=False)
    expiry_date = Column(Date, nullable=False, index=True)
    received_quantity = Column(Numeric(14, 2), nullable=False, server_default="0")
    available_quantity = Column(Numeric(14, 2), nullable=False, server_default="0")
    unit_cost = Column(Numeric(15, 2), nullable=False, server_default="0")
    supplier = Column(String(200), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    active = Column(String(1), nullable=False, server_default="Y")
    note = Column(Text, nullable=True)

    __table_args__ = (
        Index("uq_drug_batches_drug_lot_expiry", "drug_id", "lot_number", "expiry_date", unique=True),
        Index("ix_drug_batches_available_expiry", "drug_id", "available_quantity", "expiry_date"),
    )


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    drug_id = Column(Integer, ForeignKey("drugs.id", ondelete="RESTRICT"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("drug_batches.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Numeric(14, 2), nullable=False, comment="Signed quantity: positive in, negative out")
    transaction_type = Column(String(30), nullable=False, index=True)
    source_type = Column(String(50), nullable=True)
    source_id = Column(Integer, nullable=True)
    reference = Column(String(100), nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_inventory_transactions_source", "source_type", "source_id"),
    )
