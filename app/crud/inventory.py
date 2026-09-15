"""Transactional batch inventory operations using FEFO allocation."""
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Drug
from app.models.inventory import DrugBatch, InventoryTransaction
from app.schemas.inventory import BatchAdjust, BatchDispense, BatchReceive


class CRUDInventory:
    async def receive(self, db: AsyncSession, data: BatchReceive, actor_id: int) -> DrugBatch:
        if data.expiry_date < date.today():
            raise ValueError("Không thể nhập lô thuốc đã hết hạn.")
        drug = await db.scalar(select(Drug).where(Drug.id == data.drug_id).with_for_update())
        if not drug:
            raise LookupError("Không tìm thấy thuốc.")
        batch = await db.scalar(
            select(DrugBatch)
            .where(
                DrugBatch.drug_id == data.drug_id,
                DrugBatch.lot_number == data.lot_number,
                DrugBatch.expiry_date == data.expiry_date,
            )
            .with_for_update()
        )
        if not batch:
            batch = DrugBatch(
                drug_id=data.drug_id,
                lot_number=data.lot_number,
                expiry_date=data.expiry_date,
                received_quantity=data.quantity,
                available_quantity=data.quantity,
                unit_cost=data.unit_cost,
                supplier=data.supplier,
                note=data.note,
            )
            db.add(batch)
        else:
            batch.received_quantity += data.quantity
            batch.available_quantity += data.quantity
            batch.unit_cost = data.unit_cost
            batch.supplier = data.supplier or batch.supplier
        drug.stock_quantity += int(data.quantity)
        await db.flush()
        db.add(InventoryTransaction(
            drug_id=data.drug_id,
            batch_id=batch.id,
            quantity=data.quantity,
            transaction_type="receive",
            actor_id=actor_id,
            reason=data.note,
        ))
        await db.flush()
        return batch

    async def adjust(self, db: AsyncSession, data: BatchAdjust, actor_id: int) -> DrugBatch:
        batch = await db.scalar(select(DrugBatch).where(DrugBatch.id == data.batch_id).with_for_update())
        if not batch:
            raise LookupError("Không tìm thấy lô thuốc.")
        new_available = batch.available_quantity + data.quantity
        if new_available < 0:
            raise ValueError("Số lượng điều chỉnh làm tồn lô bị âm.")
        drug = await db.scalar(select(Drug).where(Drug.id == batch.drug_id).with_for_update())
        batch.available_quantity = new_available
        drug.stock_quantity += int(data.quantity)
        if drug.stock_quantity < 0:
            raise ValueError("Số lượng điều chỉnh làm tồn thuốc bị âm.")
        db.add(InventoryTransaction(
            drug_id=batch.drug_id,
            batch_id=batch.id,
            quantity=data.quantity,
            transaction_type="adjustment",
            actor_id=actor_id,
            reason=data.reason,
        ))
        await db.flush()
        return batch

    async def dispense(self, db: AsyncSession, data: BatchDispense, actor_id: int) -> list[DrugBatch]:
        drug = await db.scalar(select(Drug).where(Drug.id == data.drug_id).with_for_update())
        if not drug:
            raise LookupError("Không tìm thấy thuốc.")
        remaining = data.quantity
        batches = list((await db.scalars(
            select(DrugBatch)
            .where(
                DrugBatch.drug_id == data.drug_id,
                DrugBatch.available_quantity > 0,
                DrugBatch.expiry_date >= date.today(),
                DrugBatch.active == "Y",
            )
            .order_by(DrugBatch.expiry_date.asc(), DrugBatch.id.asc())
            .with_for_update()
        )).all())
        used: list[DrugBatch] = []
        for batch in batches:
            if remaining <= 0:
                break
            taken = min(batch.available_quantity, remaining)
            batch.available_quantity -= taken
            remaining -= taken
            used.append(batch)
            db.add(InventoryTransaction(
                drug_id=data.drug_id,
                batch_id=batch.id,
                quantity=-taken,
                transaction_type="dispense",
                source_type=data.source_type,
                source_id=data.source_id,
                reference=data.reference,
                actor_id=actor_id,
                reason=data.reason,
            ))
        if remaining > 0:
            raise ValueError("Không đủ tồn kho khả dụng theo lô còn hạn.")
        drug.stock_quantity -= int(data.quantity)
        await db.flush()
        return used

    async def list_batches(self, db: AsyncSession, drug_id: int, include_expired: bool = False):
        query = select(DrugBatch).where(DrugBatch.drug_id == drug_id)
        if not include_expired:
            query = query.where(DrugBatch.expiry_date >= date.today())
        result = await db.scalars(query.order_by(DrugBatch.expiry_date.asc(), DrugBatch.id.asc()))
        return list(result.all())

    async def list_transactions(self, db: AsyncSession, drug_id: Optional[int] = None, limit: int = 100):
        query = select(InventoryTransaction)
        if drug_id is not None:
            query = query.where(InventoryTransaction.drug_id == drug_id)
        result = await db.scalars(query.order_by(InventoryTransaction.created_at.desc()).limit(limit))
        return list(result.all())


crud_inventory = CRUDInventory()
