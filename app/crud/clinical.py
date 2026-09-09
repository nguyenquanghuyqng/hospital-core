"""
CRUD cho kết quả CLS và kiểm tra tương tác thuốc.
"""
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.clinical import ClsResult, ClsResultValue
from app.models.examination import PrescriptionItem
from app.models.catalog import Drug
from app.models.enums import ClsResultStatus
from app.schemas.clinical import ClsResultUpdate, DrugWarning


class CRUDClsResult(CRUDBase[ClsResult]):
    """CRUD cho kết quả CLS."""

    async def get_full(self, db: AsyncSession, result_id: int) -> Optional[ClsResult]:
        """Lấy ClsResult kèm values."""
        row = await db.execute(
            select(ClsResult)
            .options(selectinload(ClsResult.values))
            .where(ClsResult.id == result_id)
        )
        return row.scalar_one_or_none()

    async def get_by_prescription_item(
        self, db: AsyncSession, prescription_item_id: int
    ) -> Optional[ClsResult]:
        row = await db.execute(
            select(ClsResult)
            .options(selectinload(ClsResult.values))
            .where(ClsResult.prescription_item_id == prescription_item_id)
        )
        return row.scalar_one_or_none()

    async def list_by_examination(
        self, db: AsyncSession, examination_id: int
    ) -> List[ClsResult]:
        """Lấy tất cả kết quả CLS của một phiếu khám."""
        rows = await db.execute(
            select(ClsResult)
            .options(selectinload(ClsResult.values))
            .where(ClsResult.examination_id == examination_id)
            .order_by(ClsResult.id)
        )
        return list(rows.scalars().all())

    async def list_pending(
        self,
        db: AsyncSession,
        *,
        department: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ClsResult], int]:
        """Danh sách CLS đang chờ kết quả (cho màn hình khoa CLS)."""
        conditions = [ClsResult.status.in_([
            ClsResultStatus.PENDING, ClsResultStatus.IN_PROCESS
        ])]
        if department:
            conditions.append(ClsResult.department == department)

        query = select(ClsResult).where(and_(*conditions))
        total = (await db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar_one()
        items = list((await db.execute(
            query.options(selectinload(ClsResult.values))
            .order_by(ClsResult.created_at)
            .offset(skip).limit(limit)
        )).scalars().all())
        return items, total

    async def create_for_item(
        self,
        db: AsyncSession,
        *,
        prescription_item: PrescriptionItem,
    ) -> ClsResult:
        """
        Tự động tạo ClsResult khi thêm PrescriptionItem CLS vào phiếu khám.
        Gọi từ examination endpoint sau khi add_prescription_item thành công.
        """
        result = ClsResult(
            prescription_item_id=prescription_item.id,
            examination_id=prescription_item.examination_id,
            patient_id=(await db.get(PrescriptionItem, prescription_item.id)).examination.patient_id
            if False else prescription_item.examination_id,  # sẽ được set từ caller
            service_code=prescription_item.item_code,
            service_name=prescription_item.item_name,
            status=ClsResultStatus.PENDING,
        )
        db.add(result)
        await db.flush()
        await db.refresh(result)
        return result

    async def create_for_item_data(
        self,
        db: AsyncSession,
        *,
        prescription_item_id: int,
        examination_id: int,
        patient_id: int,
        service_code: Optional[str],
        service_name: str,
        department: Optional[str] = None,
    ) -> ClsResult:
        """Tạo ClsResult với dữ liệu đầy đủ truyền vào."""
        result = ClsResult(
            prescription_item_id=prescription_item_id,
            examination_id=examination_id,
            patient_id=patient_id,
            service_code=service_code,
            service_name=service_name,
            department=department,
            status=ClsResultStatus.PENDING,
        )
        db.add(result)
        await db.flush()
        await db.refresh(result)
        return result

    async def update_result(
        self,
        db: AsyncSession,
        *,
        db_obj: ClsResult,
        obj_in: ClsResultUpdate,
    ) -> ClsResult:
        """Cập nhật kết quả CLS và các chỉ số."""
        data = obj_in.model_dump(exclude_unset=True, exclude={"values"})

        # Tự động set performed_at / result_at nếu chuyển trạng thái
        if data.get("status") == ClsResultStatus.IN_PROCESS and not db_obj.performed_at:
            data["performed_at"] = datetime.now(timezone.utc)
        if data.get("status") == ClsResultStatus.COMPLETED and not db_obj.result_at:
            data["result_at"] = datetime.now(timezone.utc)

        for k, v in data.items():
            setattr(db_obj, k, v)
        db.add(db_obj)

        # Replace values nếu được truyền vào
        if obj_in.values is not None:
            await db.execute(
                ClsResultValue.__table__.delete().where(
                    ClsResultValue.cls_result_id == db_obj.id
                )
            )
            any_abnormal = False
            for idx, val in enumerate(obj_in.values):
                vdata = val.model_dump()
                vdata["cls_result_id"] = db_obj.id
                vdata["sort_order"] = idx
                # Tự động đánh dấu bất thường nếu ngoài khoảng ref
                if (vdata.get("value_numeric") is not None
                        and vdata.get("ref_min") is not None
                        and vdata.get("ref_max") is not None):
                    if not (vdata["ref_min"] <= vdata["value_numeric"] <= vdata["ref_max"]):
                        vdata["is_abnormal"] = True
                if vdata.get("is_abnormal"):
                    any_abnormal = True
                db.add(ClsResultValue(**vdata))

            # Sync is_abnormal lên ClsResult
            if obj_in.values:
                db_obj.is_abnormal = any_abnormal
                db.add(db_obj)

        await db.flush()
        return await self.get_full(db, db_obj.id)

    async def check_all_completed(
        self, db: AsyncSession, examination_id: int
    ) -> bool:
        """Kiểm tra tất cả CLS của phiếu đã có kết quả chưa."""
        result = await db.execute(
            select(func.count())
            .where(
                and_(
                    ClsResult.examination_id == examination_id,
                    ClsResult.status != ClsResultStatus.COMPLETED,
                    ClsResult.status != ClsResultStatus.CANCELLED,
                )
            )
        )
        pending_count = result.scalar_one()
        return pending_count == 0


# ─── Drug Interaction Service ─────────────────────────────────────────────────

async def check_drug_interactions(
    db: AsyncSession, drug_codes: List[str]
) -> List[DrugWarning]:
    """
    Kiểm tra tương tác / trùng hoạt chất giữa danh sách thuốc.

    Logic:
    1. Lấy thông tin tất cả thuốc trong danh sách.
    2. Với mỗi cặp thuốc, kiểm tra trùng active_ingredient.
    3. Trả về danh sách cảnh báo (hiện tại chỉ check trùng hoạt chất;
       có thể mở rộng thêm bảng drug_interactions sau).

    Args:
        db: Async database session.
        drug_codes: Danh sách mã thuốc cần kiểm tra.

    Returns:
        Danh sách :class:`~app.schemas.clinical.DrugWarning`.
    """
    # Lấy thông tin tất cả drugs
    rows = await db.execute(
        select(Drug).where(Drug.drug_code.in_(drug_codes))
    )
    drugs = list(rows.scalars().all())

    warnings: List[DrugWarning] = []

    # Nhóm theo active_ingredient (normalize: lowercase, strip)
    ingredient_map: dict[str, list] = {}
    for drug in drugs:
        if not drug.active_ingredient:
            continue
        # Một thuốc có thể chứa nhiều hoạt chất phân cách bằng dấu phẩy
        for ingredient in drug.active_ingredient.split(","):
            ing = ingredient.strip().lower()
            if not ing:
                continue
            ingredient_map.setdefault(ing, []).append(drug)

    # Phát cảnh báo cho hoạt chất trùng
    for ingredient, drug_list in ingredient_map.items():
        if len(drug_list) < 2:
            continue
        for i in range(len(drug_list)):
            for j in range(i + 1, len(drug_list)):
                a, b = drug_list[i], drug_list[j]
                warnings.append(DrugWarning(
                    warning_type="duplicate_ingredient",
                    severity="warning",
                    drug_a_code=a.drug_code,
                    drug_a_name=a.drug_name,
                    drug_b_code=b.drug_code,
                    drug_b_name=b.drug_name,
                    ingredient=ingredient,
                    message=(
                        f"Thuốc '{a.drug_name}' và '{b.drug_name}' "
                        f"cùng chứa hoạt chất '{ingredient}'. "
                        f"Nguy cơ tăng liều không mong muốn."
                    ),
                ))

    return warnings


async def check_drug_interactions_for_exam(
    db: AsyncSession, examination_id: int
) -> List[DrugWarning]:
    """
    Kiểm tra tương tác tất cả thuốc đang kê trong phiếu khám.
    Gọi ngay sau khi bác sĩ thêm thuốc mới.
    """
    rows = await db.execute(
        select(PrescriptionItem.item_code)
        .where(
            and_(
                PrescriptionItem.examination_id == examination_id,
                PrescriptionItem.item_type == "drug",
                PrescriptionItem.item_code.isnot(None),
            )
        )
    )
    codes = [r[0] for r in rows.all()]
    if len(codes) < 2:
        return []
    return await check_drug_interactions(db, codes)


crud_cls_result = CRUDClsResult(ClsResult)
