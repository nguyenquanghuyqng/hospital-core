"""
Validation các ràng buộc bắt buộc theo quy định BYT trước khi tạo đơn thuốc.

Các quy tắc:
  1. Số điện thoại BN bắt buộc trên MỌI đơn.
  2. Cân nặng bắt buộc nếu BN dưới 72 tháng tuổi.
  3. Tên bố/mẹ/người đưa trẻ bắt buộc nếu BN dưới 72 tháng tuổi.
  4. Đợt dùng thuốc (treatment_from, treatment_to) bắt buộc với đơn N/H.
  5. CCCD người nhận bắt buộc với đơn N/H.
  6. Không được kê thực phẩm chức năng (drug_category=functional_food) trong đơn.
  7. Bác sĩ phải có mã liên thông và license_status = active.
  8. Cảnh báo (không chặn) nếu hiệu lực đơn > 5 ngày.
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status


# ── Helpers ───────────────────────────────────────────────────────────────────

def age_in_months(date_of_birth: Optional[date]) -> Optional[int]:
    """
    Tính tuổi bệnh nhân tính theo tháng.

    Args:
        date_of_birth: Ngày sinh bệnh nhân. ``None`` → trả ``None``.

    Returns:
        Số tháng tuổi, hoặc ``None`` nếu không có ngày sinh.
    """
    if date_of_birth is None:
        return None
    today = date.today()
    months = (today.year - date_of_birth.year) * 12 + (today.month - date_of_birth.month)
    if today.day < date_of_birth.day:
        months -= 1
    return max(0, months)


def is_under_72_months(date_of_birth: Optional[date]) -> bool:
    """Kiểm tra BN có dưới 72 tháng tuổi không."""
    age = age_in_months(date_of_birth)
    return age is not None and age < 72


# ── Validation functions ───────────────────────────────────────────────────────

def validate_prescription_prerequisites(
    *,
    doctor_national_code: Optional[str],
    doctor_license_status: str,
    patient_phone: Optional[str],
    patient_date_of_birth: Optional[date],
    patient_weight_kg: Optional[Decimal],
    guardian_name: Optional[str],
    prescription_type: str,          # "N", "H", "C" — đã phân loại
    treatment_from: Optional[date],
    treatment_to: Optional[date],
    recipient_cccd: Optional[str],
    has_functional_food_items: bool,
) -> list[str]:
    """
    Kiểm tra tất cả ràng buộc bắt buộc BYT.

    Trả về danh sách thông báo lỗi (rỗng = hợp lệ).
    Caller quyết định có raise HTTPException hay không.

    Args:
        doctor_national_code: Mã liên thông bác sĩ.
        doctor_license_status: Trạng thái hành nghề ("active"/"suspended"/"revoked").
        patient_phone: Số điện thoại bệnh nhân.
        patient_date_of_birth: Ngày sinh bệnh nhân.
        patient_weight_kg: Cân nặng bệnh nhân.
        guardian_name: Tên bố/mẹ/người đưa trẻ.
        prescription_type: "N" / "H" / "C".
        treatment_from: Đợt dùng thuốc từ ngày.
        treatment_to: Đợt dùng thuốc đến ngày.
        recipient_cccd: CCCD người nhận thuốc N/H.
        has_functional_food_items: Có item nào là thực phẩm chức năng.

    Returns:
        List[str]: Danh sách thông báo lỗi (tiếng Việt).
    """
    errors: list[str] = []

    # ── 1. Kiểm tra mã liên thông bác sĩ ─────────────────────────────────────
    if not doctor_national_code:
        errors.append(
            "Bác sĩ chưa được gán mã liên thông quốc gia. "
            "Liên hệ admin để cập nhật trước khi kê đơn."
        )
    elif doctor_license_status == "suspended":
        errors.append(
            "Mã hành nghề của bác sĩ đang bị tạm dừng. "
            "Không thể kê đơn thuốc điện tử."
        )
    elif doctor_license_status == "revoked":
        errors.append(
            "Mã hành nghề của bác sĩ đã bị thu hồi. "
            "Không thể kê đơn thuốc điện tử."
        )

    # ── 2. Số điện thoại bắt buộc trên mọi đơn ───────────────────────────────
    if not patient_phone or not patient_phone.strip():
        errors.append("Số điện thoại bệnh nhân là bắt buộc trên mọi đơn thuốc điện tử.")

    # ── 3. Trẻ dưới 72 tháng — cân nặng + tên bố/mẹ ─────────────────────────
    if is_under_72_months(patient_date_of_birth):
        if patient_weight_kg is None:
            errors.append(
                "Cân nặng bệnh nhân là bắt buộc đối với trẻ dưới 72 tháng tuổi."
            )
        elif patient_weight_kg <= 0:
            errors.append("Cân nặng bệnh nhân phải lớn hơn 0.")

        if not guardian_name or not guardian_name.strip():
            errors.append(
                "Tên bố/mẹ hoặc người đưa trẻ đến khám là bắt buộc "
                "đối với bệnh nhân dưới 72 tháng tuổi."
            )

    # ── 4. Đơn N/H — đợt dùng thuốc bắt buộc ────────────────────────────────
    if prescription_type in ("N", "H"):
        if not treatment_from:
            errors.append(
                f"Đơn thuốc loại {prescription_type} bắt buộc phải có "
                "'Đợt dùng thuốc từ ngày'."
            )
        if not treatment_to:
            errors.append(
                f"Đơn thuốc loại {prescription_type} bắt buộc phải có "
                "'Đợt dùng thuốc đến ngày'."
            )
        if treatment_from and treatment_to and treatment_from > treatment_to:
            errors.append("Ngày bắt đầu đợt dùng thuốc phải trước ngày kết thúc.")

        if not recipient_cccd or not recipient_cccd.strip():
            errors.append(
                f"Đơn thuốc loại {prescription_type} bắt buộc phải có "
                "CCCD/CMND người nhận thuốc."
            )

    # ── 5. Chặn thực phẩm chức năng ──────────────────────────────────────────
    if has_functional_food_items:
        errors.append(
            "Không được kê thực phẩm chức năng (TPCN) trong đơn thuốc chính thức. "
            "Vui lòng xóa các sản phẩm TPCN khỏi đơn."
        )

    return errors


def raise_if_invalid(errors: list[str]) -> None:
    """
    Raise HTTPException 422 nếu có lỗi validation.

    Args:
        errors: Danh sách thông báo lỗi từ :func:`validate_prescription_prerequisites`.

    Raises:
        HTTPException 422: Với danh sách lỗi trong ``detail``.
    """
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": errors, "code": "PRESCRIPTION_VALIDATION_FAILED"},
        )


def check_prescription_validity_warning(items_valid_to: list[Optional[date]]) -> list[str]:
    """
    Kiểm tra hiệu lực đơn thuốc — cảnh báo (không chặn) nếu hết hạn trong 5 ngày.

    Args:
        items_valid_to: Danh sách ``valid_to`` của các PrescriptionItem.

    Returns:
        List[str]: Danh sách cảnh báo (rỗng = không có vấn đề).
    """
    warnings: list[str] = []
    today = date.today()
    max_days = 5

    for vt in items_valid_to:
        if vt and 0 <= (vt - today).days <= max_days:
            warnings.append(
                f"Đơn thuốc hết hiệu lực ngày {vt.strftime('%d/%m/%Y')} "
                f"(trong vòng {max_days} ngày)."
            )
            break  # Cảnh báo 1 lần là đủ

    return warnings
