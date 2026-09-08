"""
CRUD operations cho Examination, Diagnosis, và PrescriptionItem.

Quản lý toàn bộ vòng đời phiếu khám bệnh: tạo mới với chẩn đoán và
kê đơn đi kèm, cập nhật, chuyển trạng thái (DRAFT → SAVED → COMPLETED),
và các thao tác thêm/xoá từng dòng chẩn đoán / kê đơn riêng lẻ.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.examination import Examination, Diagnosis, PrescriptionItem
from app.models.enums import ExaminationStatus
from app.schemas.examination import (
    ExaminationCreate, ExaminationUpdate,
    DiagnosisCreate, PrescriptionItemCreate, CostSummary,
)


# ─── Helper functions ─────────────────────────────────────────────────────────

def _calc_cost(items: List[PrescriptionItem]) -> CostSummary:
    """
    Tính tổng chi phí từ danh sách dòng kê đơn / chỉ định CLS.

    Phân loại chi phí theo ``item_type``: ``drug`` (thuốc) và ``cls`` (cận lâm sàng).
    Nếu ``total_amount`` chưa có, tự tính từ ``quantity × unit_price``.

    Args:
        items: Danh sách :class:`~app.models.examination.PrescriptionItem`.

    Returns:
        :class:`~app.schemas.examination.CostSummary` với các tổng:
        ``drug_total``, ``cls_total``, ``grand_total``,
        ``bhyt_pays``, ``patient_pays``.
    """
    drug_total   = Decimal("0")
    cls_total    = Decimal("0")
    bhyt_pays    = Decimal("0")
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
    """
    Thay thế toàn bộ danh sách chẩn đoán của một phiếu khám.

    Xoá tất cả :class:`~app.models.examination.Diagnosis` hiện có rồi
    insert lại từ danh sách mới. ``sort_order`` được gán theo thứ tự list.

    Args:
        db: Async database session.
        examination_id: ID của phiếu khám cần cập nhật chẩn đoán.
        items: Danh sách :class:`~app.schemas.examination.DiagnosisCreate` mới.
    """
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
    """
    Thay thế toàn bộ danh sách kê đơn / chỉ định CLS của một phiếu khám.

    Xoá tất cả :class:`~app.models.examination.PrescriptionItem` hiện có
    rồi insert lại từ danh sách mới. Tự tính ``total_amount`` nếu chưa có.

    Args:
        db: Async database session.
        examination_id: ID của phiếu khám cần cập nhật kê đơn.
        items: Danh sách :class:`~app.schemas.examination.PrescriptionItemCreate` mới.
    """
    await db.execute(
        PrescriptionItem.__table__.delete().where(
            PrescriptionItem.examination_id == examination_id
        )
    )
    for idx, p in enumerate(items):
        data = p.model_dump()
        data["examination_id"] = examination_id
        data["sort_order"] = idx
        # Tính total_amount tự động nếu chưa có
        if data.get("total_amount") is None and data.get("unit_price") is not None:
            data["total_amount"] = Decimal(str(data["quantity"])) * Decimal(str(data["unit_price"]))
        db.add(PrescriptionItem(**data))


# ─── CRUD class ───────────────────────────────────────────────────────────────

class CRUDExamination(CRUDBase[Examination]):
    """
    CRUD class cho Examination — kế thừa :class:`~app.crud.base.CRUDBase`.

    Bổ sung: eager-load đầy đủ quan hệ (diagnoses + prescription_items + doctor),
    tạo phiếu khám cùng lúc với chẩn đoán và kê đơn, cập nhật với replace-all
    cho các collection con, và các workflow transitions (save / complete).
    Hỗ trợ thêm/xoá từng dòng chẩn đoán / kê đơn độc lập.
    """

    async def get_full(
        self, db: AsyncSession, examination_id: int
    ) -> Optional[Examination]:
        """
        Lấy phiếu khám đầy đủ với eager-load toàn bộ quan hệ.

        Load kèm: ``diagnoses``, ``prescription_items``, ``doctor``.

        Args:
            db: Async database session.
            examination_id: ID phiếu khám.

        Returns:
            :class:`~app.models.examination.Examination` với các collection đã load,
            hoặc ``None`` nếu không tìm thấy.
        """
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
        """
        Lấy phiếu khám theo ``reception_id`` (quan hệ 1-1).

        Load kèm: ``diagnoses``, ``prescription_items``.

        Args:
            db: Async database session.
            reception_id: ID của :class:`~app.models.reception.Reception`.

        Returns:
            :class:`~app.models.examination.Examination` nếu đã tạo phiếu,
            hoặc ``None`` nếu lượt tiếp đón chưa có phiếu khám.
        """
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
        """
        Lịch sử khám của bệnh nhân, sắp xếp mới nhất trước.

        Load kèm ``diagnoses`` để hiển thị chẩn đoán tóm tắt trong danh sách.

        Args:
            db: Async database session.
            patient_id: ID bệnh nhân.
            skip: Offset phân trang.
            limit: Số bản ghi tối đa.

        Returns:
            Danh sách :class:`~app.models.examination.Examination`
            kèm ``diagnoses`` đã load.
        """
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
        Tạo phiếu khám mới kèm chẩn đoán và kê đơn / chỉ định CLS.

        Tự động ghi ``exam_start_at`` = thời điểm hiện tại nếu chưa cung cấp.
        ``sort_order`` của diagnoses và prescription_items được gán theo thứ tự list.
        Tự tính ``total_amount`` cho từng dòng kê đơn nếu chưa có.

        Args:
            db: Async database session.
            obj_in: Schema :class:`~app.schemas.examination.ExaminationCreate`.

        Returns:
            :class:`~app.models.examination.Examination` đầy đủ (kết quả của
            :meth:`get_full`) với tất cả collection đã load.
        """
        data = obj_in.model_dump(exclude={"diagnoses", "prescription_items"})
        if not data.get("exam_date"):
            data["exam_date"] = date.today()
        if not data.get("exam_start_at"):
            data["exam_start_at"] = datetime.now(timezone.utc)

        exam = Examination(**data)
        db.add(exam)
        await db.flush()  # lấy exam.id để dùng cho các collection con

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
        Cập nhật phiếu khám với replace-all cho collection con.

        Nếu ``diagnoses`` được truyền vào → xoá tất cả chẩn đoán cũ và thay bằng mới.
        Nếu ``prescription_items`` được truyền vào → tương tự với kê đơn.
        Nếu không truyền (``None``) → giữ nguyên collection hiện có.

        Args:
            db: Async database session.
            db_obj: Instance :class:`~app.models.examination.Examination` hiện có.
            obj_in: Schema :class:`~app.schemas.examination.ExaminationUpdate`.

        Returns:
            :class:`~app.models.examination.Examination` đã cập nhật (kết quả
            của :meth:`get_full`).
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
        """
        Chuyển phiếu khám sang trạng thái SAVED (DRAFT → SAVED).

        Lưu tạm phiếu khám — bác sĩ có thể tiếp tục chỉnh sửa.

        Args:
            db: Async database session.
            db_obj: Instance :class:`~app.models.examination.Examination` đang ở DRAFT.

        Returns:
            :class:`~app.models.examination.Examination` đã cập nhật sang SAVED.
        """
        db_obj.status = ExaminationStatus.SAVED
        db.add(db_obj)
        await db.flush()
        return await self.get_full(db, db_obj.id)

    async def complete_examination(
        self, db: AsyncSession, *, db_obj: Examination
    ) -> Examination:
        """
        Kết thúc phiếu khám (→ COMPLETED) và ghi thời điểm kết thúc.

        Ghi ``exam_end_at`` = UTC now và ``exam_end_date`` = hôm nay.
        Sau khi COMPLETED, phiếu không thể chỉnh sửa thêm.

        Args:
            db: Async database session.
            db_obj: Instance :class:`~app.models.examination.Examination` cần kết thúc.

        Returns:
            :class:`~app.models.examination.Examination` đã cập nhật sang COMPLETED.
        """
        db_obj.status       = ExaminationStatus.COMPLETED
        db_obj.exam_end_at   = datetime.now(timezone.utc)
        db_obj.exam_end_date = date.today()
        db.add(db_obj)
        await db.flush()
        return await self.get_full(db, db_obj.id)

    async def get_cost_summary(
        self, db: AsyncSession, examination_id: int
    ) -> CostSummary:
        """
        Tính tổng chi phí real-time của phiếu khám.

        Truy vấn toàn bộ :class:`~app.models.examination.PrescriptionItem`
        của phiếu rồi tính tổng bằng :func:`_calc_cost`.

        Args:
            db: Async database session.
            examination_id: ID phiếu khám.

        Returns:
            :class:`~app.schemas.examination.CostSummary` với chi phí tổng hợp.
        """
        result = await db.execute(
            select(PrescriptionItem).where(
                PrescriptionItem.examination_id == examination_id
            )
        )
        items = list(result.scalars().all())
        return _calc_cost(items)

    # ── Diagnosis CRUD độc lập ────────────────────────────────────────────────

    async def add_diagnosis(
        self, db: AsyncSession, *, examination_id: int, obj_in: DiagnosisCreate
    ) -> Diagnosis:
        """
        Thêm một dòng chẩn đoán vào phiếu khám đang mở.

        ``sort_order`` được tính tự động bằng ``MAX(sort_order) + 1``
        để giữ đúng thứ tự thêm vào.

        Args:
            db: Async database session.
            examination_id: ID phiếu khám cần thêm chẩn đoán.
            obj_in: Schema :class:`~app.schemas.examination.DiagnosisCreate`.

        Returns:
            :class:`~app.models.examination.Diagnosis` vừa tạo.
        """
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
        """
        Xoá một dòng chẩn đoán theo ID.

        Args:
            db: Async database session.
            diagnosis_id: ID của :class:`~app.models.examination.Diagnosis` cần xoá.

        Returns:
            ``True`` nếu xoá thành công, ``False`` nếu không tìm thấy.
        """
        result = await db.execute(
            select(Diagnosis).where(Diagnosis.id == diagnosis_id)
        )
        diag = result.scalar_one_or_none()
        if diag:
            await db.delete(diag)
            await db.flush()
            return True
        return False

    # ── PrescriptionItem CRUD độc lập ─────────────────────────────────────────

    async def add_prescription_item(
        self, db: AsyncSession, *, examination_id: int, obj_in: PrescriptionItemCreate
    ) -> PrescriptionItem:
        """
        Thêm một dòng kê đơn / chỉ định CLS vào phiếu khám đang mở.

        ``sort_order`` được tính tự động. Tự tính ``total_amount`` nếu
        có ``unit_price`` và ``quantity`` nhưng chưa có ``total_amount``.

        Args:
            db: Async database session.
            examination_id: ID phiếu khám cần thêm kê đơn.
            obj_in: Schema :class:`~app.schemas.examination.PrescriptionItemCreate`.

        Returns:
            :class:`~app.models.examination.PrescriptionItem` vừa tạo.
        """
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
        """
        Xoá một dòng kê đơn / chỉ định CLS theo ID.

        Args:
            db: Async database session.
            item_id: ID của :class:`~app.models.examination.PrescriptionItem` cần xoá.

        Returns:
            ``True`` nếu xoá thành công, ``False`` nếu không tìm thấy.
        """
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
"""Singleton instance của :class:`CRUDExamination` dùng toàn ứng dụng."""
