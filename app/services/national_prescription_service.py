"""
NationalPrescriptionService — đẩy đơn thuốc lên hệ thống quốc gia BYT
(donthuocquocgia.vn) và quản lý retry tự động.

Tích hợp:
  - Gọi API BYT ngay sau khi bác sĩ hoàn tất phiếu khám (real-time, ngoại trú).
  - Retry tự động theo backoff: 5 → 15 → 30 → 60 → 120 phút (tối đa 5 lần).
  - Background retry task chạy định kỳ mỗi 3 phút.
  - Đơn nội trú (is_inpatient=True) KHÔNG push real-time.

Cấu hình (từ environment / system_config):
  NATIONAL_RX_API_URL   — Base URL API BYT (VD: https://donthuocquocgia.vn/api)
  NATIONAL_RX_API_KEY   — API key do Sở Y tế cấp
  NATIONAL_RX_TIMEOUT   — Timeout seconds (mặc định 15)

Khi chưa cấu hình NATIONAL_RX_API_URL:
  Service log warning và gán push_status = ERROR (không crash).
"""
import asyncio
import json
import logging
from datetime import date, datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud.prescription import crud_prescription
from app.models.prescription import Prescription
from app.models.enums import PrescriptionPushStatus
from app.schemas.prescription import PrescriptionCreate

logger = logging.getLogger(__name__)

# Cờ bảo vệ — chỉ chạy 1 background retry task tại 1 thời điểm
_retry_task_running = False


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_byt_payload(prescription: Prescription) -> dict:
    """
    Xây dựng JSON payload gửi lên API BYT theo schema chuẩn.

    Schema tham khảo theo tài liệu kỹ thuật donthuocquocgia.vn.
    (Thực tế schema có thể khác — cần đối chiếu tài liệu khi tích hợp thật.)

    Args:
        prescription: Prescription instance với đầy đủ thông tin.

    Returns:
        dict: JSON payload sẵn sàng gửi.
    """
    items = []
    for item in (prescription.prescription_items or []):
        items.append({
            "maThuoc":       item.item_code or "",
            "tenThuoc":      item.item_name,
            "donVi":         item.unit or "",
            "soLuong":       str(item.quantity),
            "cachDung":      item.usage_instruction or "",
            "tuNgay":        item.valid_from.isoformat() if item.valid_from else None,
            "denNgay":       item.valid_to.isoformat() if item.valid_to else None,
        })

    gender_map = {1: "1", 2: "2", 3: "3"}

    return {
        "maDon":            prescription.prescription_code,
        "maCoSo":           prescription.facility_code or "",
        "maBacSi":          prescription.doctor_national_code or "",
        "tenBacSi":         prescription.doctor_name or "",
        "loaiDon":          prescription.prescription_type.value,
        "hinhThucDieuTri":  "1" if prescription.is_inpatient else "2",
        "sdtBenhNhan":      prescription.patient_phone or "",
        "gioiTinh":         gender_map.get(prescription.patient_gender_code, ""),
        "canNang":          str(prescription.patient_weight_kg) if prescription.patient_weight_kg else "",
        "nguoiGiamHo":      prescription.guardian_name or "",
        "nguoiNhan":        prescription.recipient_name or "",
        "cccdNguoiNhan":    prescription.recipient_cccd or "",
        "tuNgayDotDung":    prescription.treatment_from.isoformat() if prescription.treatment_from else "",
        "denNgayDotDung":   prescription.treatment_to.isoformat() if prescription.treatment_to else "",
        "danhSachThuoc":    items,
        "thoiDiemKeDon":    prescription.created_at.isoformat() if prescription.created_at else "",
    }


async def push_prescription_to_national_system(
    db: AsyncSession,
    prescription: Prescription,
) -> bool:
    """
    Gửi một đơn thuốc lên hệ thống quốc gia BYT.

    Cập nhật push_status, sent_at, national_ref_id, error_log trong DB.

    Args:
        db: Async database session (có transaction đang mở).
        prescription: Prescription instance cần gửi.

    Returns:
        True nếu thành công, False nếu thất bại.
    """
    api_url = getattr(settings, "national_rx_api_url", None)
    api_key = getattr(settings, "national_rx_api_key", None)

    if not api_url:
        logger.warning(
            "NATIONAL_RX_API_URL chưa cấu hình — prescription %d gán ERROR.",
            prescription.id,
        )
        await crud_prescription.update_push_status(
            db, prescription, PrescriptionPushStatus.ERROR,
            error_info={"reason": "NATIONAL_RX_API_URL not configured"},
        )
        return False

    payload = _build_byt_payload(prescription)

    # Cập nhật trạng thái SENDING
    await crud_prescription.update_push_status(
        db, prescription, PrescriptionPushStatus.SENDING,
    )

    timeout = getattr(settings, "national_rx_timeout", 15)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{api_url}/don-thuoc",
                json=payload,
                headers={
                    "X-Api-Key": api_key or "",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            resp_data = resp.json()

        national_ref_id = resp_data.get("maDonQuocGia") or resp_data.get("id")
        await crud_prescription.update_push_status(
            db, prescription, PrescriptionPushStatus.SUCCESS,
            national_ref_id=national_ref_id,
        )
        logger.info(
            "Prescription %d (code=%s) pushed successfully. national_ref=%s",
            prescription.id, prescription.prescription_code, national_ref_id,
        )
        return True

    except httpx.HTTPStatusError as exc:
        error_body = {}
        try:
            error_body = exc.response.json()
        except Exception:
            error_body = {"raw": exc.response.text[:500]}

        # Kiểm tra nếu BYT báo mã liên thông bị thu hồi
        error_code = str(error_body.get("errorCode", "")).upper()
        if error_code in ("MA_LIEN_THONG_THU_HOI", "DOCTOR_CODE_REVOKED", "REVOKED"):
            logger.error(
                "Mã liên thông bác sĩ %s bị thu hồi theo phản hồi BYT.",
                prescription.doctor_national_code,
            )
            # Đánh dấu để admin xử lý
            error_body["__license_revoked__"] = prescription.doctor_national_code

        await crud_prescription.update_push_status(
            db, prescription, PrescriptionPushStatus.ERROR,
            error_info={
                "http_status": exc.response.status_code,
                "body": error_body,
            },
        )
        logger.error(
            "Prescription %d HTTP error %d: %s",
            prescription.id, exc.response.status_code, error_body,
        )
        return False

    except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as exc:
        await crud_prescription.update_push_status(
            db, prescription, PrescriptionPushStatus.ERROR,
            error_info={"reason": "network_error", "detail": str(exc)},
        )
        logger.warning("Prescription %d network error: %s", prescription.id, exc)
        return False

    except Exception as exc:
        await crud_prescription.update_push_status(
            db, prescription, PrescriptionPushStatus.ERROR,
            error_info={"reason": "unexpected_error", "detail": str(exc)},
        )
        logger.exception("Prescription %d unexpected error", prescription.id)
        return False


# ── Background retry task ──────────────────────────────────────────────────────

async def run_retry_task(db_factory) -> None:
    """
    Background task chạy định kỳ, retry các đơn bị lỗi.

    Được gọi từ ``startup_event`` trong ``main.py`` với asyncio.create_task().
    Lặp vô hạn, sleep 3 phút giữa các lần chạy.

    Args:
        db_factory: Async callable trả về AsyncSession (thường là ``get_db``).
    """
    global _retry_task_running
    if _retry_task_running:
        logger.warning("Retry task đang chạy — bỏ qua lần gọi này.")
        return

    _retry_task_running = True
    logger.info("Prescription retry background task started.")

    try:
        while True:
            await asyncio.sleep(180)  # 3 phút
            try:
                async for db in db_factory():
                    pending = await crud_prescription.get_pending_retry(db)
                    if pending:
                        logger.info("Retry task: %d prescriptions to retry.", len(pending))
                    for presc in pending:
                        await push_prescription_to_national_system(db, presc)
            except Exception as exc:
                logger.exception("Retry task loop error: %s", exc)
    finally:
        _retry_task_running = False
