"""
Service sinh mã đơn thuốc 14 ký tự theo chuẩn Bộ Y tế Việt Nam.

Format mã đơn: ``XXXXXYYYYYYY-Z``
  - ``XXXXX``   (5 ký tự) : mã liên thông cơ sở do Sở Y tế cấp.
  - ``YYYYYYY`` (7 ký tự) : chuỗi ngẫu nhiên alphanumeric uppercase,
                             UNIQUE trong phạm vi một cơ sở (đảm bảo bởi
                             unique constraint trên cột ``prescription_code``).
  - ``-``       (1 ký tự) : dấu phân cách.
  - ``Z``       (1 ký tự) : phân loại đơn:
                             ``N`` = gây nghiện,
                             ``H`` = hướng thần / tiền chất,
                             ``C`` = đơn khác.

Tổng: 5 + 7 + 1 + 1 = 14 ký tự (dấu ``-`` không tính theo spec nhưng
dùng để dễ đọc; nhiều hệ thống BYT chấp nhận cả 2 format).
"""
import logging
import random
import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prescription import Prescription

logger = logging.getLogger(__name__)

_ALPHABET = string.ascii_uppercase + string.digits  # A-Z 0-9 → 36 ký tự
_RANDOM_LEN = 7
_MAX_ATTEMPTS = 20  # Vòng lặp tối đa trước khi raise — không nên xảy ra


def _random_suffix() -> str:
    """Sinh 7 ký tự ngẫu nhiên alphanumeric uppercase."""
    return "".join(random.choices(_ALPHABET, k=_RANDOM_LEN))


async def generate_prescription_code(
    db: AsyncSession,
    facility_code: str,
    prescription_type: str,  # "N" | "H" | "C"
) -> str:
    """
    Sinh mã đơn thuốc 14 ký tự duy nhất cho cơ sở.

    Thuật toán:
    1. Sinh 7 ký tự ngẫu nhiên.
    2. Ghép thành ``XXXXXYYYYYYY-Z``.
    3. Kiểm tra tồn tại trong DB.
    4. Nếu trùng → thử lại (tối đa :data:`_MAX_ATTEMPTS` lần).
    5. Nếu không trùng → trả về.

    Unique constraint trên ``prescriptions.prescription_code`` là lớp bảo vệ
    cuối cùng — trong trường hợp race condition, DB sẽ raise IntegrityError
    và caller cần retry transaction.

    Args:
        db: Async database session.
        facility_code: 5 ký tự mã cơ sở từ ``system_config.national_facility_code``.
        prescription_type: "N", "H", hoặc "C".

    Returns:
        Chuỗi mã đơn 14 ký tự, ví dụ ``"ABCDE1234567-C"``.

    Raises:
        RuntimeError: Không thể sinh mã duy nhất sau :data:`_MAX_ATTEMPTS` lần thử.
    """
    fc = (facility_code or "").strip().upper()
    if len(fc) != 5 or not fc.isalnum():
        raise ValueError(
            "Mã liên thông cơ sở phải gồm đúng 5 ký tự chữ hoặc số "
            "trước khi tạo đơn thuốc."
        )

    for attempt in range(_MAX_ATTEMPTS):
        suffix = _random_suffix()
        code = f"{fc}{suffix}-{prescription_type}"

        # Kiểm tra tồn tại
        result = await db.execute(
            select(Prescription.id).where(Prescription.prescription_code == code)
        )
        if result.scalar_one_or_none() is None:
            logger.debug("Generated prescription code %s (attempt %d)", code, attempt + 1)
            return code

        logger.warning("Prescription code collision: %s (attempt %d)", code, attempt + 1)

    raise RuntimeError(
        f"Không thể sinh mã đơn duy nhất sau {_MAX_ATTEMPTS} lần thử. "
        "Kiểm tra lại cấu hình facility_code."
    )


def classify_prescription_type(drug_categories: list[str]) -> str:
    """
    Phân loại đơn thuốc dựa trên danh mục nhóm thuốc được kê.

    Logic theo quy định BYT:
    - Có ≥1 thuốc ``narcotic``      → ``"N"``
    - Có ≥1 thuốc ``psychotropic``  → ``"H"``  (và không có narcotic)
    - Còn lại                        → ``"C"``

    Args:
        drug_categories: Danh sách giá trị ``drug_category`` của các PrescriptionItem.

    Returns:
        ``"N"``, ``"H"``, hoặc ``"C"``.
    """
    cats = set(drug_categories)
    if "narcotic" in cats:
        return "N"
    if "psychotropic" in cats:
        return "H"
    return "C"
