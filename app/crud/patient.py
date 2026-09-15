"""
CRUD operations cho model :class:`~app.models.patient.Patient`.

Cung cấp tra cứu, tìm kiếm full-text, sinh mã bệnh nhân tự động,
và thao tác tạo/cập nhật hồ sơ bệnh nhân.
"""
from datetime import date
from typing import List, Optional
import re
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate


def _generate_patient_code(year: int, seq: int) -> str:
    """
    Sinh mã bệnh nhân theo định dạng 8 ký tự: ``YYnnnnnn``.

    Hai ký tự đầu là 2 chữ số cuối của năm (ví dụ 26 cho năm 2026),
    6 ký tự còn lại là số thứ tự trong năm, zero-padded 6 chữ số.

    Args:
        year: Năm hiện tại (4 chữ số, VD: 2026).
        seq: Số thứ tự trong năm (padding thành 6 chữ số).

    Returns:
        Mã bệnh nhân dạng chuỗi 8 ký tự, VD: ``"26000001"``.
    """
    # Format: 2-digit year (YY) + 6-digit zero-padded sequence
    return f"{year % 100:02d}{seq:06d}"


class CRUDPatient(CRUDBase[Patient]):
    """
    CRUD class cho Patient — kế thừa :class:`~app.crud.base.CRUDBase`.

    Bổ sung: tra cứu theo CCCD/mã BN, tìm kiếm full-text,
    sinh mã BN tự động, và upsert theo CCCD.
    """

    # ── Tra cứu ─────────────────────────────────────────────────────────────

    async def get_by_cccd(self, db: AsyncSession, cccd: str) -> Optional[Patient]:
        # Normalize CCCD: remove non-digit characters to allow lookups with spaces/dashes
        if cccd is None:
            return None
        normalized = re.sub(r"\D", "", cccd)
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
            select(Patient).where(Patient.cccd == normalized)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, db: AsyncSession, patient_code: str) -> Optional[Patient]:
        """
        Tìm bệnh nhân theo mã bệnh nhân (patient_code).

        Args:
            db: Async database session.
            patient_code: Mã bệnh nhân dạng 8 ký tự ``YYnnnnnn`` (ví dụ ``26000001``).

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
        Sinh mã bệnh nhân tiếp theo trong năm hiện tại theo định dạng ``YYnnnnnn``.

        Logic:
        - Tìm mã bệnh nhân lớn nhất bắt đầu bằng 2 chữ số cuối của năm hiện tại (YY)
          và tăng sequence lên 1.
        - Trả về mã mới ở dạng 8 ký tự (YY + 6 chữ số sequence zero-padded).

        Args:
            db: Async database session.

        Returns:
            Mã bệnh nhân mới chưa tồn tại trong database, VD: ``"26000001"``.
        """
        year = date.today().year
        year_short = f"{year % 100:02d}"

        # Tìm patient_code lớn nhất bắt đầu bằng year_short (ví dụ '26%')
        result = await db.execute(
            select(func.max(Patient.patient_code)).where(
                Patient.patient_code.like(f"{year_short}%")
            )
        )
        last_code: Optional[str] = result.scalar_one_or_none()

        if last_code:
            # last_code expected format: YY + 6-digit sequence
            try:
                seq_part = last_code[len(year_short):]
                seq = int(seq_part) + 1
            except (ValueError, IndexError):
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
        1. Tự sinh ``patient_code`` dạng 8 ký tự ``YYnnnnnn`` nếu chưa có (ví dụ ``26000001``).
        2. Tự điền ``birth_year`` từ ``date_of_birth`` nếu thiếu.

        Args:
            db: Async database session.
            obj_in: Schema :class:`~app.schemas.patient.PatientCreate` chứa dữ liệu bệnh nhân.

        Returns:
            :class:`~app.models.patient.Patient` vừa được tạo.
        """
        data = obj_in.model_dump()

        # Normalize CCCD stored value
        if data.get("cccd"):
            data["cccd"] = re.sub(r"\D", "", str(data.get("cccd")))

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


    async def get_by_identifier(self, db: AsyncSession, identifier: str) -> Optional[Patient]:
        """
        Tra cứu thông minh: luôn dò cả hai cột CCCD và patient_code.

        Giải pháp:
        - Chuẩn hoá input (loại bỏ ký tự không phải số để so sánh CCCD).
        - Thử lookup theo CCCD (nếu có chữ số nào đó) — trả ngay khi tìm thấy.
        - Sau đó thử lookup theo patient_code (chuyển uppercase) — trả khi tìm thấy.
        - Nếu không tìm thấy ở cả hai, trả None.

        Mục tiêu: bất kể người dùng nhập CCCD hay mã BN ở các định dạng khác nhau,
        endpoint vẫn tìm được hồ sơ nếu tồn tại ở một trong hai cột.
        """
        if not identifier:
            return None
        ident = str(identifier).strip()
        # Normalize digits for CCCD lookup
        digits = re.sub(r"\D", "", ident)

        # 1) Try CCCD lookup if any digits present
        if digits:
            patient = await self.get_by_cccd(db, digits)
            if patient:
                return patient

        # 2) Try patient_code lookup (normalize to uppercase)
        code = ident.upper()
        patient = await self.get_by_code(db, code)
        if patient:
            return patient

        # 3) If input contains only digits or common variants, build candidate patient_code forms
        candidates = []
        if digits:
            # Direct BN + digits
            candidates.append(f'BN{digits}')

            # If digits look like YYYY + seq, produce BNYYYY + seq(zfilled to 6)
            if len(digits) >= 5:
                year_part = digits[:4]
                seq_part = digits[4:]
                if year_part.isdigit():
                    seq_padded = seq_part.zfill(6)
                    candidates.append(f'BN{year_part}{seq_padded}')
                    # Also add the short-year format YY + seq (new format)
                    candidates.append(f'{year_part[-2:]}{seq_padded}')

            # Also try current year + padded seq (both BNYYYY... legacy and new YY... formats)
            cur_year = date.today().year
            candidates.append(f'BN{cur_year}{digits.zfill(6)}')
            candidates.append(f'{cur_year % 100:02d}{digits.zfill(6)}')

        # Deduplicate and try lookup by patient_code for each candidate
        seen = set()
        for cand in candidates:
            cand_up = cand.upper()
            if cand_up in seen:
                continue
            seen.add(cand_up)
            patient = await self.get_by_code(db, cand_up)
            if patient:
                return patient

        # 4) As a last effort, if original input had BN prefix with non-digits, try stripping non-digits
        if ident.upper().startswith('BN'):
            alt = re.sub(r"\D", "", ident)
            if alt:
                alt_code = ('BN' + alt) if not alt.upper().startswith('BN') else alt.upper()
                patient = await self.get_by_code(db, alt_code)
                if patient:
                    return patient

        return None


crud_patient = CRUDPatient(Patient)
"""Singleton instance của :class:`CRUDPatient` dùng toàn ứng dụng."""
