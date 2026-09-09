"""
Service xuất XML BHYT theo chuẩn Thông tư 48/2017/TT-BYT (và phụ lục).

Cấu trúc XML cơ bản (phiên bản rút gọn cho phòng khám ngoại trú)::

    <HSBADSLuu>
      <HSBADSMa>          — Mã đợt khám
      <BVMaCSKCB>         — Mã cơ sở KCB
      <TTDieuTri>         — Thông tin điều trị (1 lượt = 1 element)
        <MaBN>            — Mã bệnh nhân
        <HoTen>           — Họ tên
        <NgaySinh>        — Ngày sinh dd/MM/yyyy
        <GioiTinh>        — 1=Nam, 2=Nữ
        <DiaChi>          — Địa chỉ
        <SoTheBHYT>       — Số thẻ BHYT
        <MaCSKCB>         — Mã nơi ĐKKCB ban đầu
        <NgayVao>         — dd/MM/yyyy
        <NgayRa>          — dd/MM/yyyy
        <MaBenh>          — Mã ICD-10 chẩn đoán chính
        <TenBenh>         — Tên bệnh
        <MaBenhKemTheo>   — Mã ICD-10 chẩn đoán kèm (nhiều, phân cách ;)
        <PhuongPhapDieuTri> — NKLN (nội khoa lấy ngày)
        <KetQua>          — 1=Khỏi, 2=Đỡ, 3=Không đổi, 4=Nặng hơn, 5=Tử vong
        <TiLeThanhToan>   — Tỷ lệ BHYT chi trả (80, 95, 100...)
        <T_BHASD>         — Số tiền BHYT chi trả
        <T_BN>            — Số tiền bệnh nhân chi trả
        <T_TONG>          — Tổng chi phí
        <ChiTietDichVu>   — Chi tiết từng dịch vụ CLS + thuốc
          <DichVu>
            <MaDV>
            <TenDV>
            <DVT>
            <SoLuong>
            <DonGia>
            <ThanhTien>
            <MHBT>        — Mức hưởng BT
"""
import json
from datetime import date
from decimal import Decimal
from typing import Optional
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.examination import Examination, Diagnosis, PrescriptionItem
from app.models.patient import Patient
from app.models.billing import Bill
from app.models.catalog import SystemConfig


def _fmt_date(d: Optional[date]) -> str:
    """Định dạng ngày theo chuẩn BYT: dd/MM/yyyy."""
    if d is None:
        return ""
    return d.strftime("%d/%m/%Y")


def _gender_code(gender: Optional[str]) -> str:
    """Chuyển gender text → mã BYT (1=Nam, 2=Nữ, 0=Không xác định)."""
    if not gender:
        return "0"
    g = gender.lower()
    if g in ("male", "nam", "m"):
        return "1"
    if g in ("female", "nữ", "nu", "f"):
        return "2"
    return "0"


def _result_code(revisit_result: Optional[str]) -> str:
    """
    Chuyển revisit_result text → mã kết quả BYT.
    1=Khỏi, 2=Đỡ/ra viện, 3=Không thay đổi, 4=Nặng hơn, 5=Tử vong.
    """
    if not revisit_result:
        return "2"
    r = revisit_result.lower()
    if "khỏi" in r or "khoi" in r:
        return "1"
    if "đỡ" in r or "do" in r or "tốt" in r or "tot" in r:
        return "2"
    if "nặng" in r or "nang" in r:
        return "4"
    if "tử vong" in r or "tu vong" in r:
        return "5"
    return "2"


async def _get_config(db: AsyncSession, key: str, default: str = "") -> str:
    row = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    cfg = row.scalar_one_or_none()
    return cfg.value if cfg and cfg.value else default


async def build_bhyt_xml(
    db: AsyncSession,
    examination_ids: list[int],
    *,
    batch_code: Optional[str] = None,
) -> bytes:
    """
    Tạo XML BHYT cho một hoặc nhiều phiếu khám.

    Args:
        db: Async DB session.
        examination_ids: Danh sách ID phiếu khám cần xuất.
        batch_code: Mã đợt xuất (tự sinh nếu None).

    Returns:
        XML bytes (UTF-8, pretty-printed).

    Raises:
        ValueError: Phiếu khám không tồn tại hoặc chưa COMPLETED.
    """
    # Đọc config cơ sở
    facility_code = await _get_config(db, "facility_code", "")
    facility_name = await _get_config(db, "facility_name", "Phòng khám")
    bhyt_contract = await _get_config(db, "bhyt_contract_no", "")
    bhyt_copay    = await _get_config(db, "bhyt_copay_rate", "0.20")
    try:
        default_copay_rate = int(float(bhyt_copay) * 100)
    except (ValueError, TypeError):
        default_copay_rate = 80

    if not batch_code:
        from datetime import date as _date
        batch_code = f"DT{_date.today().strftime('%Y%m%d')}"

    # Root element
    root = Element("HSBADSLuu")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    SubElement(root, "HSBADSMa").text       = batch_code
    SubElement(root, "BVMaCSKCB").text      = facility_code
    SubElement(root, "SoHDBHYT").text       = bhyt_contract
    SubElement(root, "NgayXuat").text       = _fmt_date(date.today())
    SubElement(root, "SoLuotKham").text     = str(len(examination_ids))

    # Load tất cả phiếu khám
    rows = await db.execute(
        select(Examination)
        .options(
            selectinload(Examination.diagnoses),
            selectinload(Examination.prescription_items),
        )
        .where(Examination.id.in_(examination_ids))
    )
    examinations = list(rows.scalars().all())

    for exam in examinations:
        # Load patient
        p_row = await db.execute(select(Patient).where(Patient.id == exam.patient_id))
        patient = p_row.scalar_one_or_none()

        # Load bill nếu có
        b_row = await db.execute(select(Bill).where(Bill.examination_id == exam.id))
        bill = b_row.scalar_one_or_none()

        # Chẩn đoán chính
        primary_diag = next(
            (d for d in exam.diagnoses if d.is_primary), 
            exam.diagnoses[0] if exam.diagnoses else None
        )
        secondary_diags = [d for d in exam.diagnoses if not d.is_primary]

        # Tổng tiền
        grand_total = bill.grand_total if bill else Decimal("0")
        bhyt_pays   = bill.bhyt_pays   if bill else Decimal("0")
        patient_pays = bill.patient_pays if bill else Decimal("0")
        copay_rate  = default_copay_rate

        tt = SubElement(root, "TTDieuTri")

        # Thông tin bệnh nhân
        SubElement(tt, "MaBN").text      = (patient.patient_code or str(exam.patient_id)) if patient else str(exam.patient_id)
        SubElement(tt, "HoTen").text     = patient.full_name if patient else ""
        SubElement(tt, "NgaySinh").text  = _fmt_date(patient.date_of_birth) if patient and patient.date_of_birth else (
            f"01/01/{patient.birth_year}" if patient and patient.birth_year else ""
        )
        SubElement(tt, "GioiTinh").text  = _gender_code(patient.gender if patient else None)
        SubElement(tt, "DiaChi").text    = (patient.address or "") if patient else ""
        SubElement(tt, "CCCD").text      = (patient.cccd or "") if patient else ""

        # BHYT
        SubElement(tt, "SoTheBHYT").text    = exam.insurance_number or ""
        SubElement(tt, "HanThe_Tu").text    = _fmt_date(exam.insurance_valid_from)
        SubElement(tt, "HanThe_Den").text   = _fmt_date(exam.insurance_valid_to)
        SubElement(tt, "MaCSKCBBanDau").text = exam.referral_from_name or facility_code
        SubElement(tt, "MaLoaiKCB").text    = "1"  # 1 = ngoại trú

        # Ngày khám
        SubElement(tt, "NgayVao").text   = _fmt_date(exam.exam_date)
        SubElement(tt, "NgayRa").text    = _fmt_date(exam.exam_end_date or exam.exam_date)
        SubElement(tt, "GioVao").text    = exam.exam_start_at.strftime("%H:%M") if exam.exam_start_at else ""
        SubElement(tt, "GioRa").text     = exam.exam_end_at.strftime("%H:%M")   if exam.exam_end_at   else ""

        # Chẩn đoán
        SubElement(tt, "MaBenh").text    = primary_diag.icd_code  if primary_diag else ""
        SubElement(tt, "TenBenh").text   = primary_diag.icd_name  if primary_diag else ""
        SubElement(tt, "MaBenhKemTheo").text = ";".join(
            d.icd_code for d in secondary_diags if d.icd_code
        )

        # Phương pháp / kết quả
        SubElement(tt, "PhuongPhapDieuTri").text = "NKLN"
        SubElement(tt, "KetQua").text = _result_code(exam.revisit_result)
        SubElement(tt, "GiaiBenhNhan").text = "1"  # 1 = ra viện thông thường

        # Bác sĩ
        SubElement(tt, "MaBS").text     = str(exam.doctor_id or "")
        SubElement(tt, "HoTenBS").text  = exam.doctor_name or ""

        # Chi phí
        SubElement(tt, "TiLeThanhToan").text = str(copay_rate)
        SubElement(tt, "T_TONG").text        = str(grand_total)
        SubElement(tt, "T_BHASD").text       = str(bhyt_pays)
        SubElement(tt, "T_BN").text          = str(patient_pays)

        # Chi tiết dịch vụ
        cd = SubElement(tt, "ChiTietDichVu")
        for item in exam.prescription_items:
            dv = SubElement(cd, "DichVu")
            SubElement(dv, "MaDV").text      = item.item_code or ""
            SubElement(dv, "TenDV").text     = item.item_name
            SubElement(dv, "DVT").text       = item.unit or "lần"
            SubElement(dv, "SoLuong").text   = str(item.quantity)
            SubElement(dv, "DonGia").text    = str(item.unit_price or "0")
            SubElement(dv, "ThanhTien").text = str(item.total_amount or "0")
            SubElement(dv, "BHYTThanhToan").text = str(item.bhyt_amount or "0")
            SubElement(dv, "BNThanhToan").text   = str(item.patient_amount or "0")
            # Mã hưởng BHYT: 1=thuốc, 2=VTTH, 3=dịch vụ kỹ thuật, 4=CLS
            mhbt = "1" if item.item_type == "drug" else "4"
            SubElement(dv, "MHBT").text = mhbt
            SubElement(dv, "LoaiDV").text = item.item_type

    # Pretty-print
    raw = tostring(root, encoding="unicode", xml_declaration=False)
    dom = parseString(f'<?xml version="1.0" encoding="UTF-8"?>{raw}')
    return dom.toprettyxml(indent="  ", encoding="UTF-8")
