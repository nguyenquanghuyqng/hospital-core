"""
CRUD cho viện phí (Bill, BillItem, Payment).
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.billing import Bill, BillItem, Payment
from app.models.examination import PrescriptionItem, Examination
from app.models.enums import BillStatus, PaymentMethod
from app.schemas.billing import BillCreate, BillUpdate, PaymentCreate


def _gen_bill_number(db_id: int) -> str:
    """Sinh số hóa đơn dạng HD{year}{id:06d}."""
    from datetime import date
    return f"HD{date.today().year}{db_id:06d}"


class CRUDBill(CRUDBase[Bill]):
    """CRUD cho hóa đơn viện phí."""

    async def get_full(self, db: AsyncSession, bill_id: int) -> Optional[Bill]:
        """Lấy Bill kèm items và payments."""
        row = await db.execute(
            select(Bill)
            .options(
                selectinload(Bill.items),
                selectinload(Bill.payments),
            )
            .where(Bill.id == bill_id)
        )
        return row.scalar_one_or_none()

    async def get_by_examination(
        self, db: AsyncSession, examination_id: int
    ) -> Optional[Bill]:
        row = await db.execute(
            select(Bill)
            .options(selectinload(Bill.items), selectinload(Bill.payments))
            .where(Bill.examination_id == examination_id)
        )
        return row.scalar_one_or_none()

    async def list_by_patient(
        self,
        db: AsyncSession,
        patient_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Bill], int]:
        query = select(Bill).where(Bill.patient_id == patient_id)
        total = (await db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar_one()
        items = list((await db.execute(
            query.order_by(Bill.created_at.desc()).offset(skip).limit(limit)
        )).scalars().all())
        return items, total

    async def list_bills(
        self,
        db: AsyncSession,
        *,
        status: Optional[BillStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Bill], int]:
        conditions = []
        if status:
            conditions.append(Bill.status == status)
        query = select(Bill)
        if conditions:
            query = query.where(and_(*conditions))
        total = (await db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar_one()
        items = list((await db.execute(
            query.order_by(Bill.created_at.desc()).offset(skip).limit(limit)
        )).scalars().all())
        return items, total

    async def create_from_examination(
        self,
        db: AsyncSession,
        *,
        obj_in: BillCreate,
        cashier_id: Optional[int] = None,
        cashier_name: Optional[str] = None,
    ) -> Bill:
        """
        Tạo hóa đơn từ phiếu khám đã COMPLETED.
        Tự động sinh BillItems từ PrescriptionItems.
        """
        # Load phiếu khám
        exam_row = await db.execute(
            select(Examination).where(Examination.id == obj_in.examination_id)
        )
        exam = exam_row.scalar_one_or_none()
        if not exam:
            raise ValueError(f"Examination {obj_in.examination_id} not found")

        # Load prescription items
        items_row = await db.execute(
            select(PrescriptionItem).where(
                PrescriptionItem.examination_id == obj_in.examination_id
            )
        )
        items = list(items_row.scalars().all())

        # Tính tổng
        drug_total = Decimal("0")
        cls_total  = Decimal("0")
        bhyt_pays  = Decimal("0")
        patient_pays = Decimal("0")

        for it in items:
            total = it.total_amount or (
                (it.quantity or Decimal("0")) * (it.unit_price or Decimal("0"))
            )
            if it.item_type == "drug":
                drug_total += total
            else:
                cls_total += total
            bhyt_pays    += (it.bhyt_amount    or Decimal("0"))
            patient_pays += (it.patient_amount or Decimal("0"))

        grand_total  = drug_total + cls_total
        deposit      = obj_in.deposit_amount or Decimal("0")
        discount     = obj_in.discount_amount or Decimal("0")
        balance_due  = max(Decimal("0"), patient_pays - deposit - discount)

        bill = Bill(
            bill_number    = "DRAFT",  # cập nhật sau khi flush
            examination_id = obj_in.examination_id,
            patient_id     = exam.patient_id,
            reception_id   = exam.reception_id,
            status         = BillStatus.DRAFT,
            cashier_id     = cashier_id,
            cashier_name   = cashier_name,
            drug_total     = drug_total,
            cls_total      = cls_total,
            service_total  = Decimal("0"),
            grand_total    = grand_total,
            bhyt_pays      = bhyt_pays,
            patient_pays   = patient_pays,
            discount_amount = discount,
            deposit_amount  = deposit,
            balance_due     = balance_due,
            insurance_number = exam.insurance_number,
            note           = obj_in.note,
        )
        db.add(bill)
        await db.flush()

        # Cập nhật bill_number theo id
        bill.bill_number = _gen_bill_number(bill.id)
        db.add(bill)

        # Tạo BillItems
        for idx, it in enumerate(items):
            total = it.total_amount or (
                (it.quantity or Decimal("0")) * (it.unit_price or Decimal("0"))
            )
            db.add(BillItem(
                bill_id              = bill.id,
                prescription_item_id = it.id,
                item_type            = it.item_type,
                item_code            = it.item_code,
                item_name            = it.item_name,
                unit                 = it.unit,
                quantity             = it.quantity,
                unit_price           = it.unit_price,
                payment_type         = it.payment_type,
                total_amount         = total,
                bhyt_amount          = it.bhyt_amount,
                patient_amount       = it.patient_amount,
                sort_order           = idx,
            ))

        await db.flush()
        return await self.get_full(db, bill.id)

    async def issue_bill(
        self, db: AsyncSession, *, db_obj: Bill
    ) -> Bill:
        """Phát hành hóa đơn (DRAFT → ISSUED)."""
        db_obj.status    = BillStatus.ISSUED
        db_obj.issued_at = datetime.now(timezone.utc)
        db.add(db_obj)
        await db.flush()
        return await self.get_full(db, db_obj.id)

    async def add_payment(
        self,
        db: AsyncSession,
        *,
        db_obj: Bill,
        obj_in: PaymentCreate,
        cashier_id: Optional[int] = None,
    ) -> Bill:
        """Ghi nhận một lần thanh toán và cập nhật trạng thái bill."""
        payment = Payment(
            bill_id         = db_obj.id,
            cashier_id      = cashier_id,
            payment_method  = obj_in.payment_method,
            amount          = obj_in.amount,
            paid_at         = datetime.now(timezone.utc),
            transaction_ref = obj_in.transaction_ref,
            note            = obj_in.note,
            is_deposit      = obj_in.is_deposit,
            is_refund       = obj_in.is_refund,
        )
        db.add(payment)

        # Cập nhật deposit nếu là tạm ứng
        if obj_in.is_deposit:
            db_obj.deposit_amount += obj_in.amount
        elif obj_in.is_refund:
            db_obj.deposit_amount -= obj_in.amount

        # Tính tổng đã thanh toán (không tính deposit và refund)
        db_obj.balance_due = max(
            Decimal("0"),
            db_obj.patient_pays - db_obj.deposit_amount - db_obj.discount_amount
        )
        if db_obj.balance_due == 0 and db_obj.status == BillStatus.ISSUED:
            db_obj.status  = BillStatus.PAID
            db_obj.paid_at = datetime.now(timezone.utc)
        elif db_obj.status == BillStatus.ISSUED:
            db_obj.status  = BillStatus.PARTIAL
        db.add(db_obj)
        await db.flush()
        return await self.get_full(db, db_obj.id)

    async def cancel_bill(
        self, db: AsyncSession, *, db_obj: Bill
    ) -> Bill:
        db_obj.status = BillStatus.CANCELLED
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_bill(
        self, db: AsyncSession, *, db_obj: Bill, obj_in: BillUpdate
    ) -> Bill:
        data = obj_in.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(db_obj, k, v)
        # Recalculate balance_due
        if "discount_amount" in data or "deposit_amount" in data:
            db_obj.balance_due = max(
                Decimal("0"),
                db_obj.patient_pays - db_obj.deposit_amount - db_obj.discount_amount
            )
        db.add(db_obj)
        await db.flush()
        return await self.get_full(db, db_obj.id)


crud_bill = CRUDBill(Bill)
