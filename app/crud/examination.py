"""
CRUD cho Examination, Diagnosis, PrescriptionItem.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, func, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.examination import Examination, Diagnosis, PrescriptionItem
from app.models.enums import ExaminationStatus
from app.schemas.examination import (
    ExaminationCreate, ExaminationUpdate,
    DiagnosisCreate, PrescriptionItemCreate, CostSummary,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _calc_cost(items: List[PrescriptionItem]) -> CostSummary:
    drug_total  = Decimal("0")
    cls_total   = Decimal("0")
    bhyt_pays   = Decimal("0")
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

    grand_total = drug_total + cls_total
    return CostSummary(
        drug_total=drug_total,
        cls_total=cls_total,
        grand_total=grand_total,
        bhyt_pays=bhyt_pays,
        patient_pays=patient_pays,
    )


async def _replace_diagnoses(
    db: AsyncSession,
    examination_id: int,
    items: List[DiagnosisCreate],
) -> None:
    await db.execute(
        Diagnosis.__table__.delete().where(
            Diagnosis.examination_id == examination_id
        )
    )
    for idx, d in enumerate(items):
        data = d.model_dump()
        data["examination_id"] = examination_id
        data["sort_order"] = idx
        db.add(Diagnosis(**data))


async def _replace_prescriptions(
    db: AsyncSession,
    examination_id: int,
    items: List[PrescriptionItemCreate],
) -> None:
    await db.execute(
        PrescriptionItem.__table__.delete().where(
            PrescriptionItem.examination_id == examination_id
        )
    )
    for idx, p in enumerate(items):
        data = p.model_dump()
        data["examination_id"] = examination_id
        data["sort_order"] = idx
        # tính total_amount tự động nếu chưa có
        if data.get("total_amount") is None and data.get("unit_price") is not None:
            data["total_amount"] = Decimal(str(data["quantity"])) * Decimal(str(data["unit_price"]))
        db.add(PrescriptionItem(**data))


# ─── CRUD ─────────────────────────────────────────────────────────────────────

class CRUDExamination(CRUDBase[Examination]):

    async def get_full(
        self, db: AsyncSession, examination_id: int
    ) -> Optional[Examination]:
        """Lấy phiếu khám kèm diagnoses + prescription_items."""
        result = await db.execute(
            select(Examination)
            .options(
                selectinload(Examination.diagnoses),
                selectinload(Examination.prescription_items),
                selectinload(Examination.doctor),
            )
            .where(Examination.id == examination_id)
        )
        return result.scalar_one_or_none()

    async def get_by_reception(
        self, db: AsyncSession, reception_id: int
    ) -> Optional[Examination]:
        """Lấy phiếu khám theo reception_id (1-1)."""
        result = await db.execute(
            select(Examination)
            .options(
                selectinload(Examination.diagnoses),
                selectinload(Examination.prescription_items),
            )
            .where(Examination.reception_id == reception_id)
        )
        return result.scalar_one_or_none()

    async def get_history(
        self,
        db: AsyncSession,
        patient_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Examination]:
        """Lịch sử khám của bệnh nhân — kèm diagnoses (tóm tắt)."""
        result = await db.execute(
            select(Examination)
            .options(selectinload(Examination.diagnoses))
            .where(Examination.patient_id == patient_id)
            .order_by(Examination.exam_date.desc(), Examination.id.desc())
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create_examination(
        self, db: AsyncSession, *, obj_in: ExaminationCreate
    ) -> Examination:
        """
        Tạo phiếu khám mới kèm diagnoses + prescription_items.
        Tự ghi exam_start_at = now nếu chưa có.
        """
        data = obj_in.model_dump(exclude={"diagnoses", "prescription_items"})
        if not data.get("exam_date"):
            data["exam_date"] = date.today()
        if not data.get("exam_start_at"):
            data["exam_start_at"] = datetime.now(timezone.utc)

        exam = Examination(**data)
        db.add(exam)
        await db.flush()  # lấy exam.id

        for idx, d in enumerate(obj_in.diagnoses):
            dd = d.model_dump()
            dd["examination_id"] = exam.id
            dd["sort_order"] = idx
            db.add(Diagnosis(**dd))

        for idx, p in enumerate(obj_in.prescription_items):
            pp = p.model_dump()
            pp["examination_id"] = exam.id
            pp["sort_order"] = idx
            if pp.get("total_amount") is None and pp.get("unit_price") is not None:
                pp["total_amount"] = Decimal(str(pp["quantity"])) * Decimal(str(pp["unit_price"]))
            db.add(PrescriptionItem(**pp))

        await db.flush()
        return await self.get_full(db, exam.id)

    async def update_examination(
        self,
        db: AsyncSession,
        *,
        db_obj: Examination,
        obj_in: ExaminationUpdate,
    ) -> Examination:
        """
        Cập nhật phiếu khám.
        Nếu diagnoses / prescription_items được truyền → thay thế toàn bộ.
        """
        data = obj_in.model_dump(exclude_unset=True, exclude={"diagnoses", "prescription_items"})
        for k, v in data.items():
            setattr(db_obj, k, v)
        db.add(db_obj)

        if obj_in.diagnoses is not None:
            await _replace_diagnoses(db, db_obj.id, obj_in.diagnoses)
        if obj_in.prescription_items is not None:
            await _replace_prescriptions(db, db_obj.id, obj_in.prescription_items)

        await db.flush()
        return await self.get_full(db, db_obj.id)

    async def save_examination(
        self, db: AsyncSession, *, db_obj: Examination
    ) -> Examination:
        """DRAFT → SAVED."""
        db_obj.status = ExaminationStatus.SAVED
        db.add(db_obj)
        await db.flush()
        return await self.get_full(db, db_obj.id)

    async def complete_examination(
        self, db: AsyncSession, *, db_obj: Examination
    ) -> Examination:
        """→ COMPLETED + ghi exam_end_at."""
        db_obj.status      = ExaminationStatus.COMPLETED
        db_obj.exam_end_at   = datetime.now(timezone.utc)
        db_obj.exam_end_date = date.today()
        db.add(db_obj)
        await db.flush()
        return await self.get_full(db, db_obj.id)

    async def get_cost_summary(
        self, db: AsyncSession, examination_id: int
    ) -> CostSummary:
        result = await db.execute(
            select(PrescriptionItem).where(
                PrescriptionItem.examination_id == examination_id
            )
        )
        items = list(result.scalars().all())
        return _calc_cost(items)

    # ── Diagnosis CRUD riêng ──────────────────────────────────────────────────

    async def add_diagnosis(
        self, db: AsyncSession, *, examination_id: int, obj_in: DiagnosisCreate
    ) -> Diagnosis:
        # Compute next sort_order to maintain insertion order
        result = await db.execute(
            select(func.coalesce(func.max(Diagnosis.sort_order), -1))
            .where(Diagnosis.examination_id == examination_id)
        )
        next_order = (result.scalar_one() or -1) + 1
        data = obj_in.model_dump()
        data["examination_id"] = examination_id
        data["sort_order"] = next_order
        diag = Diagnosis(**data)
        db.add(diag)
        await db.flush()
        await db.refresh(diag)
        return diag

    async def delete_diagnosis(
        self, db: AsyncSession, *, diagnosis_id: int
    ) -> bool:
        result = await db.execute(
            select(Diagnosis).where(Diagnosis.id == diagnosis_id)
        )
        diag = result.scalar_one_or_none()
        if diag:
            await db.delete(diag)
            await db.flush()
            return True
        return False

    # ── PrescriptionItem CRUD riêng ───────────────────────────────────────────

    async def add_prescription_item(
        self, db: AsyncSession, *, examination_id: int, obj_in: PrescriptionItemCreate
    ) -> PrescriptionItem:
        result = await db.execute(
            select(func.coalesce(func.max(PrescriptionItem.sort_order), -1))
            .where(PrescriptionItem.examination_id == examination_id)
        )
        next_order = (result.scalar_one() or -1) + 1
        data = obj_in.model_dump()
        data["examination_id"] = examination_id
        data["sort_order"] = next_order
        if data.get("total_amount") is None and data.get("unit_price") is not None:
            data["total_amount"] = Decimal(str(data["quantity"])) * Decimal(str(data["unit_price"]))
        item = PrescriptionItem(**data)
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item

    async def delete_prescription_item(
        self, db: AsyncSession, *, item_id: int
    ) -> bool:
        result = await db.execute(
            select(PrescriptionItem).where(PrescriptionItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if item:
            await db.delete(item)
            await db.flush()
            return True
        return False


crud_examination = CRUDExamination(Examination)
