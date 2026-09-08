"""
Generic async CRUD base class dùng chung cho mọi ORM model.

Cung cấp các thao tác cơ bản (Create / Read / Update / Delete) với
SQLAlchemy async session. Tất cả thao tác chỉ gọi ``flush()`` chứ không
``commit()`` — việc commit được uỷ quyền cho :func:`~app.db.session.get_db`.
"""
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    """
    Lớp CRUD generic có thể tái sử dụng cho bất kỳ SQLAlchemy model nào.

    Sử dụng Python Generics để đảm bảo type-safety:
    ``CRUDBase[Patient]`` chỉ làm việc với model :class:`~app.models.patient.Patient`.

    Args:
        model: Lớp SQLAlchemy model cụ thể được quản lý bởi instance này.

    Example::

        class CRUDPatient(CRUDBase[Patient]):
            ...

        crud_patient = CRUDPatient(Patient)
    """

    def __init__(self, model: Type[ModelType]):
        """
        Khởi tạo CRUD instance với model class cụ thể.

        Args:
            model: Lớp SQLAlchemy model (VD: ``Patient``, ``User``).
        """
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        """
        Lấy một bản ghi theo khoá chính.

        Args:
            db: Async database session.
            id: Giá trị khoá chính (integer).

        Returns:
            Instance model nếu tìm thấy, ``None`` nếu không tồn tại.
        """
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> List[ModelType]:
        """
        Lấy danh sách bản ghi có phân trang, sắp xếp mới nhất trước.

        Args:
            db: Async database session.
            skip: Số bản ghi bỏ qua (offset).
            limit: Số bản ghi tối đa trả về.

        Returns:
            Danh sách instances model, sắp xếp giảm dần theo ``id``.
        """
        result = await db.execute(
            select(self.model).offset(skip).limit(limit).order_by(self.model.id.desc())
        )
        return list(result.scalars().all())

    async def count(self, db: AsyncSession) -> int:
        """
        Đếm tổng số bản ghi trong bảng.

        Args:
            db: Async database session.

        Returns:
            Tổng số bản ghi (integer).
        """
        result = await db.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()

    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> ModelType:
        """
        Tạo một bản ghi mới từ dict dữ liệu.

        Gọi ``flush()`` để lấy ``id`` từ database mà không commit,
        sau đó ``refresh()`` để load lại giá trị server-side (VD: timestamps).

        Args:
            db: Async database session.
            obj_in: Dict chứa dữ liệu các cột cần insert.

        Returns:
            Instance model vừa tạo, với ``id`` và timestamps đã được điền.
        """
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[Dict[str, Any], Any],
    ) -> ModelType:
        """
        Cập nhật một bản ghi hiện có.

        Chấp nhận cả dict lẫn Pydantic schema (có ``model_dump``).
        Chỉ cập nhật các field được cung cấp (``exclude_unset=True`` với Pydantic).

        Args:
            db: Async database session.
            db_obj: Instance model đang tồn tại trong database.
            obj_in: Dữ liệu cập nhật — có thể là ``dict`` hoặc Pydantic model.

        Returns:
            Instance model đã được cập nhật và refresh.
        """
        if hasattr(obj_in, "model_dump"):
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            update_data = obj_in

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: int) -> Optional[ModelType]:
        """
        Xoá một bản ghi theo khoá chính.

        Args:
            db: Async database session.
            id: Khoá chính của bản ghi cần xoá.

        Returns:
            Instance model vừa bị xoá nếu tìm thấy, ``None`` nếu không tồn tại.
        """
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.flush()
        return obj
