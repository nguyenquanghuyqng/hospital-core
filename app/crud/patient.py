import re
from datetime import date
from typing import List, Optional
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate


def _generate_patient_code(year: int, seq: int) -> str:
    """Sinh mã bệnh nhân theo định dạng BNYYYYnnnn (VD: BN20260001)."""
    return f"BN{year}{seq:04d}"


class CRUDPatient(CRUDBase[Patient]):

    # ── Tra cứu ─────────────────────────────────────────────────────

    async def get_by_cccd(self, db: AsyncSession, cccd: str) -> Optional[Patient]:
        """Tìm bệnh nhân theo số CCCD/CMND."""
        result = await db.execute(
            select(Patient).where(Patient.cccd == cccd)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, db: AsyncSession, patient_code: str) -> Optional[Patient]:
        """Tìm bệnh nhân theo mã BN."""
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
        Tìm kiếm bệnh nhân theo:
        - Họ tên, CCCD, số điện thoại
        - Mã BN
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

    # ── Sinh mã BN ──────────────────────────────────────────────────

    async def _next_patient_code(self, db: AsyncSession) -> str:
        """
        Sinh mã BN tiếp theo trong năm hiện tại.
        Format: BNYYYYnnnn — đảm bảo không trùng.
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

    # ── Tạo / Cập nhật ───────────────────────────────────────────────

    async def create_patient(
        self, db: AsyncSession, *, obj_in: PatientCreate
    ) -> Patient:
        """
        Tạo bệnh nhân mới:
        - Tự sinh patient_code nếu chưa có.
        - Tự điền birth_year từ date_of_birth nếu thiếu.
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
        Cập nhật bệnh nhân.
        Đồng bộ birth_year nếu date_of_birth thay đổi.
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
        Tìm bệnh nhân theo CCCD, nếu chưa có thì tạo mới.
        Trả về (patient, created: bool).
        """
        if obj_in.cccd:
            existing = await self.get_by_cccd(db, obj_in.cccd)
            if existing:
                return existing, False
        patient = await self.create_patient(db, obj_in=obj_in)
        return patient, True


crud_patient = CRUDPatient(Patient)
