"""
CRUD operations cho model :class:`~app.models.patient.Patient`.

Cung cấp tra cứu, tìm kiếm full-text, sinh mã bệnh nhân tự động,
và thao tác tạo/cập nhật hồ sơ bệnh nhân.
"""
from datetime import date
from typing import List, Optional
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate


def _generate_patient_code(year: int, seq: int) -> str:
    """
    Sinh mã bệnh nhân theo định dạng ``BNYYYYnnnn``.

    Args:
        year: Năm hiện tại (4 chữ số, VD: 2026).
        seq: Số thứ tự trong năm (padding thành 4 chữ số).

    Returns:
        Mã bệnh nhân dạng chuỗi, VD: ``"BN20260001"``.
    """
    return f"BN{year}{seq:04d}"


class CRUDPatient(CRUDBase[Patient]):
    """
    CRUD class cho Patient — kế thừa :class:`~app.crud.base.CRUDBase`.

    Bổ sung: tra cứu theo CCCD/mã BN, tìm kiếm full-text,
    sinh mã BN tự động, và upsert theo CCCD.
    """

    # ── Tra cứu ─────────────────────────────────────────────────────────────

    async def get_by_cccd(self, db: AsyncSession, cccd: str) -> Optional[Patient]:
        """
        Tìm bệnh nhân theo số CCCD/CMND.

        Dùng khi quét thẻ căn cước để tra cứu nhanh bệnh nhân đã có trong hệ thống.

        Args:
            db: Async database session.
            cccd: Số CCCD hoặc CMND (9 hoặc 12 chữ số).

        Returns:
            :class:`~app.models.patient.Patient` nếu tìm thấy, ``None`` nếu không.
        """
        result = await db.execute(
            select(Patient).where(Patient.cccd == cccd)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, db: AsyncSession, patient_code: str) -> Optional[Patient]:
        """
        Tìm bệnh nhân theo mã bệnh nhân (patient_code).

        Args:
            db: Async database session.
            patient_code: Mã bệnh nhân dạng ``BNYYYYnnnn``.

        Returns:
            :class:`~app.models.patient.Patient` nếu tìm thấy, ``None`` nếu không.
        """
        result = await db.execute(
            select(Patient).where(Patient.patient_code == patient_code)
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        db: AsyncSession,
        *,
        keyword: str,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Patient]:
        """
        Tìm kiếm bệnh nhân theo từ khoá (case-insensitive).

        Tìm kiếm song song trên các trường: họ tên, CCCD, số điện thoại,
        và mã bệnh nhân.

        Args:
            db: Async database session.
            keyword: Từ khoá tìm kiếm (tìm substring, không phân biệt hoa thường).
            skip: Số kết quả bỏ qua (phân trang).
            limit: Số kết quả tối đa trả về.

        Returns:
            Danh sách :class:`~app.models.patient.Patient` phù hợp,
            sắp xếp theo họ tên tăng dần.
        """
        pattern = f"%{keyword}%"
        result = await db.execute(
            select(Patient)
            .where(
                or_(
                    Patient.full_name.ilike(pattern),
                    Patient.cccd.ilike(pattern),
                    Patient.phone.ilike(pattern),
                    Patient.patient_code.ilike(pattern),
                )
            )
            .offset(skip)
            .limit(limit)
            .order_by(Patient.full_name)
        )
        return list(result.scalars().all())

    async def count_search(self, db: AsyncSession, keyword: str) -> int:
        """
        Đếm số kết quả tìm kiếm theo từ khoá (dùng cho phân trang).

        Args:
            db: Async database session.
            keyword: Từ khoá tìm kiếm, cùng logic với :meth:`search`.

        Returns:
            Tổng số bản ghi phù hợp.
        """
        pattern = f"%{keyword}%"
        result = await db.execute(
            select(func.count()).select_from(Patient).where(
                or_(
                    Patient.full_name.ilike(pattern),
                    Patient.cccd.ilike(pattern),
                    Patient.phone.ilike(pattern),
                    Patient.patient_code.ilike(pattern),
                )
            )
        )
        return result.scalar_one()

    # ── Sinh mã BN ──────────────────────────────────────────────────────────

    async def _next_patient_code(self, db: AsyncSession) -> str:
        """
        Sinh mã bệnh nhân tiếp theo trong năm hiện tại.

        Truy vấn mã BN lớn nhất của năm hiện tại, cộng thêm 1 vào sequence.
        Format: ``BNYYYYnnnn`` — đảm bảo không trùng lặp trong cùng năm.

        Args:
            db: Async database session.

        Returns:
            Mã bệnh nhân mới chưa tồn tại trong database, VD: ``"BN20260042"``.
        """
        year = date.today().year
        prefix = f"BN{year}"
        result = await db.execute(
            select(func.max(Patient.patient_code)).where(
                Patient.patient_code.like(f"{prefix}%")
            )
        )
        last_code: Optional[str] = result.scalar_one_or_none()
        if last_code:
            try:
                seq = int(last_code[len(prefix):]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
        return _generate_patient_code(year, seq)

    # ── Tạo / Cập nhật ──────────────────────────────────────────────────────

    async def create_patient(
        self, db: AsyncSession, *, obj_in: PatientCreate
    ) -> Patient:
        """
        Tạo bệnh nhân mới với sinh mã tự động và đồng bộ năm sinh.

        Thực hiện hai bước bổ sung so với :meth:`~CRUDBase.create`:
        1. Tự sinh ``patient_code`` dạng ``BNYYYYnnnn`` nếu chưa có.
        2. Tự điền ``birth_year`` từ ``date_of_birth`` nếu thiếu.

        Args:
            db: Async database session.
            obj_in: Schema :class:`~app.schemas.patient.PatientCreate` chứa dữ liệu bệnh nhân.

        Returns:
            :class:`~app.models.patient.Patient` vừa được tạo.
        """
        data = obj_in.model_dump()

        # Tự sinh mã BN
        if not data.get("patient_code"):
            data["patient_code"] = await self._next_patient_code(db)

        # Đồng bộ birth_year ↔ date_of_birth
        if not data.get("birth_year") and data.get("date_of_birth"):
            data["birth_year"] = data["date_of_birth"].year

        return await self.create(db, obj_in=data)

    async def update_patient(
        self,
        db: AsyncSession,
        *,
        db_obj: Patient,
        obj_in: PatientUpdate,
    ) -> Patient:
        """
        Cập nhật thông tin bệnh nhân với đồng bộ năm sinh.

        Nếu ``date_of_birth`` được cập nhật mà không truyền ``birth_year``,
        tự động cập nhật ``birth_year`` theo.

        Args:
            db: Async database session.
            db_obj: Instance :class:`~app.models.patient.Patient` hiện có trong DB.
            obj_in: Schema :class:`~app.schemas.patient.PatientUpdate` chứa dữ liệu mới.

        Returns:
            :class:`~app.models.patient.Patient` đã cập nhật.
        """
        data = obj_in.model_dump(exclude_unset=True)

        # Đồng bộ birth_year ↔ date_of_birth
        if "date_of_birth" in data and data["date_of_birth"] and "birth_year" not in data:
            data["birth_year"] = data["date_of_birth"].year

        return await self.update(db, db_obj=db_obj, obj_in=data)

    async def get_or_create_by_cccd(
        self,
        db: AsyncSession,
        *,
        obj_in: PatientCreate,
    ) -> tuple[Patient, bool]:
        """
        Tìm bệnh nhân theo CCCD; nếu chưa có thì tạo mới.

        Dùng trong luồng quét CCCD tại quầy tiếp đón để tránh tạo hồ sơ
        trùng lặp cho bệnh nhân đã từng khám.

        Args:
            db: Async database session.
            obj_in: Schema :class:`~app.schemas.patient.PatientCreate`
                với ``cccd`` là trường dùng để tra cứu.

        Returns:
            Tuple ``(patient, created)`` trong đó:
            - ``patient``: instance :class:`~app.models.patient.Patient`.
            - ``created``: ``True`` nếu vừa tạo mới, ``False`` nếu đã tồn tại.
        """
        if obj_in.cccd:
            existing = await self.get_by_cccd(db, obj_in.cccd)
            if existing:
                return existing, False
        patient = await self.create_patient(db, obj_in=obj_in)
        return patient, True


crud_patient = CRUDPatient(Patient)
"""Singleton instance của :class:`CRUDPatient` dùng toàn ứng dụng."""
