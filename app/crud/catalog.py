"""
CRUD operations cho danh mục hệ thống.

Bao gồm: Drug, ClsService, Icd10, SystemConfig, AuditLog.
"""
import json
from typing import List, Optional, Tuple
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.catalog import Drug, ClsService, Icd10, SystemConfig, AuditLog
from app.schemas.catalog import (
    DrugCreate, DrugUpdate,
    ClsServiceCreate, ClsServiceUpdate,
    Icd10BulkItem,
    SystemConfigUpsert,
    AuditLogCreate,
)


# ─── Drug CRUD ────────────────────────────────────────────────────────────────

class CRUDDrug(CRUDBase[Drug]):
    """CRUD cho danh mục thuốc."""

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Drug]:
        result = await db.execute(select(Drug).where(Drug.drug_code == code))
        return result.scalar_one_or_none()

    async def search(
        self,
        db: AsyncSession,
        *,
        keyword: str = "",
        is_active: Optional[bool] = True,
        is_bhyt: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Drug], int]:
        """Tìm kiếm thuốc, trả về (items, total)."""
        query = select(Drug)
        conditions = []

        if keyword:
            pat = f"%{keyword}%"
            conditions.append(
                or_(
                    Drug.drug_name.ilike(pat),
                    Drug.drug_code.ilike(pat),
                    Drug.generic_name.ilike(pat),
                    Drug.active_ingredient.ilike(pat),
                )
            )
        if is_active is not None:
            conditions.append(Drug.is_active == is_active)
        if is_bhyt is not None:
            conditions.append(Drug.is_bhyt == is_bhyt)

        if conditions:
            query = query.where(and_(*conditions))

        total_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(total_q)).scalar_one()

        items_q = query.order_by(Drug.drug_name).offset(skip).limit(limit)
        items = list((await db.execute(items_q)).scalars().all())
        return items, total

    async def create_drug(self, db: AsyncSession, *, obj_in: DrugCreate) -> Drug:
        data = obj_in.model_dump()
        return await self.create(db, obj_in=data)

    async def update_drug(
        self, db: AsyncSession, *, db_obj: Drug, obj_in: DrugUpdate
    ) -> Drug:
        return await self.update(db, db_obj=db_obj, obj_in=obj_in)

    async def adjust_stock(
        self, db: AsyncSession, *, drug_id: int, delta: int
    ) -> Optional[Drug]:
        """Điều chỉnh tồn kho: delta dương = nhập, âm = xuất."""
        drug = await self.get(db, drug_id)
        if not drug:
            return None
        drug.stock_quantity = max(0, (drug.stock_quantity or 0) + delta)
        db.add(drug)
        await db.flush()
        await db.refresh(drug)
        return drug


# ─── ClsService CRUD ─────────────────────────────────────────────────────────

class CRUDClsService(CRUDBase[ClsService]):
    """CRUD cho danh mục dịch vụ CLS."""

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[ClsService]:
        result = await db.execute(
            select(ClsService).where(ClsService.service_code == code)
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        db: AsyncSession,
        *,
        keyword: str = "",
        service_group: Optional[str] = None,
        is_active: Optional[bool] = True,
        is_bhyt: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ClsService], int]:
        query = select(ClsService)
        conditions = []

        if keyword:
            pat = f"%{keyword}%"
            conditions.append(
                or_(
                    ClsService.service_name.ilike(pat),
                    ClsService.service_code.ilike(pat),
                )
            )
        if service_group:
            conditions.append(ClsService.service_group == service_group)
        if is_active is not None:
            conditions.append(ClsService.is_active == is_active)
        if is_bhyt is not None:
            conditions.append(ClsService.is_bhyt == is_bhyt)

        if conditions:
            query = query.where(and_(*conditions))

        total = (await db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar_one()

        items = list((await db.execute(
            query.order_by(ClsService.service_name).offset(skip).limit(limit)
        )).scalars().all())
        return items, total

    async def create_service(
        self, db: AsyncSession, *, obj_in: ClsServiceCreate
    ) -> ClsService:
        return await self.create(db, obj_in=obj_in.model_dump())

    async def update_service(
        self, db: AsyncSession, *, db_obj: ClsService, obj_in: ClsServiceUpdate
    ) -> ClsService:
        return await self.update(db, db_obj=db_obj, obj_in=obj_in)


# ─── Icd10 CRUD ───────────────────────────────────────────────────────────────

class CRUDIcd10(CRUDBase[Icd10]):
    """CRUD cho danh mục ICD-10 (thường chỉ đọc + import)."""

    async def search(
        self,
        db: AsyncSession,
        *,
        keyword: str,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Icd10]:
        """Tìm kiếm theo mã hoặc tên (tiếng Việt / Anh)."""
        pat = f"%{keyword}%"
        result = await db.execute(
            select(Icd10)
            .where(
                or_(
                    Icd10.code.ilike(pat),
                    Icd10.name_vi.ilike(pat),
                    Icd10.name_en.ilike(pat),
                )
            )
            .order_by(Icd10.code)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Icd10]:
        result = await db.execute(select(Icd10).where(Icd10.code == code))
        return result.scalar_one_or_none()

    async def bulk_upsert(
        self, db: AsyncSession, *, items: List[Icd10BulkItem]
    ) -> int:
        """
        Upsert danh sách ICD-10 từ file import.
        Trả về số dòng đã xử lý.
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        rows = [item.model_dump() for item in items]
        if not rows:
            return 0

        stmt = pg_insert(Icd10).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["code"],
            set_={
                "name_vi": stmt.excluded.name_vi,
                "name_en": stmt.excluded.name_en,
                "chapter": stmt.excluded.chapter,
                "block":   stmt.excluded.block,
                "is_leaf": stmt.excluded.is_leaf,
            },
        )
        await db.execute(stmt)
        return len(rows)


# ─── SystemConfig CRUD ────────────────────────────────────────────────────────

class CRUDSystemConfig(CRUDBase[SystemConfig]):
    """CRUD cho cấu hình cơ sở."""

    async def get_by_key(self, db: AsyncSession, key: str) -> Optional[SystemConfig]:
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        return result.scalar_one_or_none()

    async def get_value(self, db: AsyncSession, key: str) -> Optional[str]:
        """Lấy nhanh giá trị theo key."""
        cfg = await self.get_by_key(db, key)
        return cfg.value if cfg else None

    async def get_by_group(
        self, db: AsyncSession, group: str
    ) -> List[SystemConfig]:
        result = await db.execute(
            select(SystemConfig)
            .where(SystemConfig.group == group)
            .order_by(SystemConfig.key)
        )
        return list(result.scalars().all())

    async def get_all(self, db: AsyncSession) -> List[SystemConfig]:
        result = await db.execute(
            select(SystemConfig).order_by(SystemConfig.group, SystemConfig.key)
        )
        return list(result.scalars().all())

    async def upsert(
        self,
        db: AsyncSession,
        *,
        obj_in: SystemConfigUpsert,
        updated_by: Optional[str] = None,
    ) -> SystemConfig:
        """Tạo mới hoặc cập nhật config theo key."""
        existing = await self.get_by_key(db, obj_in.key)
        if existing:
            existing.value       = obj_in.value
            existing.label       = obj_in.label
            existing.group       = obj_in.group
            existing.description = obj_in.description
            existing.is_public   = obj_in.is_public
            existing.updated_by  = updated_by
            db.add(existing)
            await db.flush()
            await db.refresh(existing)
            return existing
        data = obj_in.model_dump()
        data["updated_by"] = updated_by
        return await self.create(db, obj_in=data)

    async def set_value(
        self,
        db: AsyncSession,
        *,
        key: str,
        value: Optional[str],
        updated_by: Optional[str] = None,
    ) -> Optional[SystemConfig]:
        """Cập nhật nhanh giá trị theo key đã tồn tại."""
        cfg = await self.get_by_key(db, key)
        if not cfg:
            return None
        cfg.value      = value
        cfg.updated_by = updated_by
        db.add(cfg)
        await db.flush()
        await db.refresh(cfg)
        return cfg


# ─── AuditLog CRUD ────────────────────────────────────────────────────────────

class CRUDAuditLog(CRUDBase[AuditLog]):
    """CRUD cho audit log (chỉ ghi và đọc, không update/delete)."""

    async def log(
        self,
        db: AsyncSession,
        *,
        obj_in: AuditLogCreate,
    ) -> AuditLog:
        """Ghi một entry vào audit log."""
        return await self.create(db, obj_in=obj_in.model_dump())

    async def log_change(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[int],
        username: Optional[str],
        action: str,
        table_name: str,
        record_id: Optional[int] = None,
        old_data: Optional[dict] = None,
        new_data: Optional[dict] = None,
        ip_address: Optional[str] = None,
        description: Optional[str] = None,
    ) -> AuditLog:
        """Helper tiện lợi: chuyển dict → JSON text rồi ghi log."""
        return await self.log(
            db,
            obj_in=AuditLogCreate(
                user_id=user_id,
                username=username,
                action=action,
                table_name=table_name,
                record_id=record_id,
                old_data=json.dumps(old_data, ensure_ascii=False, default=str) if old_data else None,
                new_data=json.dumps(new_data, ensure_ascii=False, default=str) if new_data else None,
                ip_address=ip_address,
                description=description,
            ),
        )

    async def get_by_record(
        self,
        db: AsyncSession,
        *,
        table_name: str,
        record_id: int,
        limit: int = 50,
    ) -> List[AuditLog]:
        """Lấy lịch sử thay đổi của một bản ghi cụ thể."""
        result = await db.execute(
            select(AuditLog)
            .where(
                and_(
                    AuditLog.table_name == table_name,
                    AuditLog.record_id == record_id,
                )
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        table_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[AuditLog], int]:
        """Lấy nhật ký gần đây với filter tuỳ chọn."""
        conditions = []
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if action:
            conditions.append(AuditLog.action == action)
        if table_name:
            conditions.append(AuditLog.table_name == table_name)

        query = select(AuditLog)
        if conditions:
            query = query.where(and_(*conditions))

        total = (await db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar_one()
        items = list((await db.execute(
            query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        )).scalars().all())
        return items, total


# ── Singleton instances ───────────────────────────────────────────────────────
crud_drug       = CRUDDrug(Drug)
crud_cls        = CRUDClsService(ClsService)
crud_icd10      = CRUDIcd10(Icd10)
crud_config     = CRUDSystemConfig(SystemConfig)
crud_audit      = CRUDAuditLog(AuditLog)
