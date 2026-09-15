"""
Prescription endpoints — đơn thuốc điện tử chuẩn Bộ Y tế.

Routes:
  GET    /prescriptions/dashboard              — Thống kê tỷ lệ gửi cho admin
  GET    /prescriptions/by-examination/{eid}   — Lấy đơn theo examination_id
  GET    /prescriptions/{id}                   — Chi tiết đơn thuốc
  PATCH  /prescriptions/{id}                   — Cập nhật thông tin phụ trợ
  POST   /prescriptions/{id}/retry             — Retry gửi thủ công
  POST   /prescriptions/{id}/cancel            — Huỷ đơn (chỉ admin)
  POST   /prescriptions/{id}/sold              — Đánh dấu đã bán
  GET    /prescriptions/{id}/qr                — Sinh QR code tra cứu
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import require_doctor, require_admin, require_cashier
from app.models.user import User
from app.models.enums import PrescriptionPushStatus
from app.crud.prescription import crud_prescription
from app.crud.catalog import crud_audit
from app.schemas.prescription import (
    PrescriptionUpdate, PrescriptionResponse, PrescriptionList, PrescriptionDashboard,
)
from app.services.national_prescription_service import push_prescription_to_national_system
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/prescriptions", tags=["Prescription - Đơn thuốc điện tử BYT"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_404(db: AsyncSession, prescription_id: int):
    """Lấy đơn thuốc hoặc raise 404."""
    obj = await crud_prescription.get_full(db, prescription_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn thuốc")
    return obj


def _get_facility_code() -> str:
    """Lấy mã cơ sở từ settings (cấu hình qua NATIONAL_FACILITY_CODE env)."""
    return getattr(settings, "national_facility_code", "") or ""


# ── Dashboard (admin) ─────────────────────────────────────────────────────────

@router.get(
    "/dashboard",
    response_model=PrescriptionDashboard,
    summary="Thống kê tỷ lệ đẩy đơn hôm nay — Admin dashboard",
)
async def prescription_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Thống kê tổng hợp tỷ lệ gửi đơn lên hệ thống quốc gia hôm nay.

    Trả về: tổng đơn, số pending/success/error/cancelled, tỷ lệ thành công %,
    lần gửi thành công gần nhất, trạng thái cấu hình facility_code.
    """
    fc = _get_facility_code()
    return await crud_prescription.dashboard_stats(db, facility_code=fc)


# ── Lấy đơn theo examination ──────────────────────────────────────────────────

@router.get(
    "/by-examination/{examination_id}",
    response_model=PrescriptionResponse,
    summary="Lấy đơn thuốc theo examination_id",
)
async def get_by_examination(
    examination_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Lấy đơn thuốc liên kết với một phiếu khám.

    Args:
        examination_id: ID phiếu khám.

    Raises:
        HTTPException 404: Chưa có đơn thuốc cho phiếu khám này.
    """
    obj = await crud_prescription.get_by_examination(db, examination_id)
    if not obj:
        raise HTTPException(
            status_code=404,
            detail="Chưa có đơn thuốc cho phiếu khám này",
        )
    return obj


# ── Chi tiết đơn ─────────────────────────────────────────────────────────────

@router.get(
    "/{prescription_id}",
    response_model=PrescriptionResponse,
    summary="Chi tiết đơn thuốc",
)
async def get_prescription(
    prescription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """Chi tiết đầy đủ một đơn thuốc theo ID."""
    return await _get_or_404(db, prescription_id)


# ── Cập nhật thông tin phụ trợ ────────────────────────────────────────────────

@router.patch(
    "/{prescription_id}",
    response_model=PrescriptionResponse,
    summary="Cập nhật thông tin đơn thuốc (chỉ khi chưa gửi thành công)",
)
async def update_prescription(
    prescription_id: int,
    obj_in: PrescriptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Cập nhật các trường phụ trợ (phone, guardian, recipient, treatment dates...).

    **Không cho phép sửa nếu push_status = success.**

    Raises:
        HTTPException 409: Đơn đã gửi thành công.
    """
    obj = await _get_or_404(db, prescription_id)

    if obj.push_status == PrescriptionPushStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Đơn đã được gửi thành công lên hệ thống quốc gia. "
                "Không thể chỉnh sửa — hãy tạo đơn mới để điều chỉnh."
            ),
        )

    try:
        updated = await crud_prescription.update(db, obj, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    await db.commit()
    return updated


# ── Retry thủ công ────────────────────────────────────────────────────────────

@router.post(
    "/{prescription_id}/retry",
    response_model=PrescriptionResponse,
    summary="Retry gửi đơn thuốc lên hệ thống quốc gia",
)
async def retry_prescription(
    prescription_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Gửi lại đơn thuốc đã thất bại.

    Chỉ cho phép retry khi push_status = error hoặc pending.
    Nếu đơn đã thành công: trả về 409.
    Retry được thực thi bất đồng bộ (background task).
    """
    obj = await _get_or_404(db, prescription_id)

    if obj.push_status == PrescriptionPushStatus.SUCCESS:
        raise HTTPException(
            status_code=409, detail="Đơn đã gửi thành công, không cần retry."
        )
    if obj.push_status == PrescriptionPushStatus.CANCELLED:
        raise HTTPException(
            status_code=409, detail="Đơn đã bị huỷ, không thể retry. Tạo đơn mới nếu cần."
        )
    if obj.push_status not in (PrescriptionPushStatus.ERROR, PrescriptionPushStatus.PENDING):
        raise HTTPException(status_code=409, detail="Đơn đang được xử lý, chưa thể retry.")
    if obj.push_status == PrescriptionPushStatus.ERROR and obj.retry_count >= 5:
        raise HTTPException(
            status_code=409,
            detail="Đơn đã vượt quá 5 lần retry tự động. Hãy tạo đơn thay thế sau khi kiểm tra lỗi.",
        )

    # Đặt lại trạng thái pending để background task pick up
    obj.push_status = PrescriptionPushStatus.PENDING
    await db.flush()
    await db.commit()
    await db.refresh(obj)

    logger.info(
        "Manual retry requested for prescription %d by user %s",
        prescription_id, current_user.username,
    )

    # Push ngay trong background
    background_tasks.add_task(
        _bg_push, prescription_id
    )

    return obj


@router.post(
    "/{prescription_id}/replacement",
    response_model=PrescriptionResponse,
    summary="Tạo đơn thay thế cho đơn đã gửi thành công",
)
async def create_replacement_prescription(
    prescription_id: int,
    obj_in: PrescriptionUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """Create a new code and preserve the old successful prescription."""
    source = await _get_or_404(db, prescription_id)
    if source.push_status != PrescriptionPushStatus.SUCCESS:
        raise HTTPException(
            status_code=409,
            detail="Chỉ đơn đã gửi thành công mới được tạo đơn thay thế.",
        )

    replacement = await crud_prescription.create_replacement(db, source)
    if obj_in.model_dump(exclude_unset=True):
        replacement = await crud_prescription.update(db, replacement, obj_in)

    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="CREATE",
        table_name="prescriptions",
        record_id=replacement.id,
        new_data={"supersedes_id": source.id, "prescription_code": replacement.prescription_code},
        description=f"Tạo đơn thay thế cho đơn #{source.id}",
    )
    await db.commit()
    replacement = await crud_prescription.get_full(db, replacement.id)
    background_tasks.add_task(_bg_push, replacement.id)
    return replacement


async def _bg_push(prescription_id: int):
    """Background task wrapper để push prescription (fresh session)."""
    from app.db.session import async_session_factory
    async with async_session_factory() as db:
        try:
            obj = await crud_prescription.get_full(db, prescription_id)
            if obj:
                await push_prescription_to_national_system(db, obj)
                await db.commit()
        except Exception as exc:
            logger.exception("Background push failed for prescription %d: %s", prescription_id, exc)


# ── Huỷ đơn (admin only) ─────────────────────────────────────────────────────

@router.post(
    "/{prescription_id}/cancel",
    response_model=PrescriptionResponse,
    summary="Huỷ đơn thuốc (admin only)",
)
async def cancel_prescription(
    prescription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Admin huỷ đơn thuốc — chỉ khi chưa gửi thành công.

    Raises:
        HTTPException 409: Đơn đã gửi thành công.
    """
    obj = await _get_or_404(db, prescription_id)
    if obj.push_status == PrescriptionPushStatus.SUCCESS:
        raise HTTPException(
            status_code=409, detail="Đơn đã gửi thành công, không thể huỷ."
        )

    obj.push_status = PrescriptionPushStatus.CANCELLED
    await db.flush()
    await db.commit()
    await db.refresh(obj)
    return obj


# ── Đánh dấu đã bán ──────────────────────────────────────────────────────────

@router.post(
    "/{prescription_id}/sold",
    response_model=PrescriptionResponse,
    summary="Đánh dấu đơn đã được bán tại nhà thuốc",
)
async def mark_sold(
    prescription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    """
    Đồng bộ trạng thái 'đã bán' khi nhà thuốc xác nhận.

    Chỉ cho phép khi push_status = success.
    """
    obj = await _get_or_404(db, prescription_id)
    if obj.push_status != PrescriptionPushStatus.SUCCESS:
        raise HTTPException(
            status_code=409,
            detail="Chỉ đánh dấu đã bán được cho đơn đã gửi thành công lên hệ thống quốc gia.",
        )

    updated = await crud_prescription.mark_sold(db, obj)
    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="UPDATE",
        table_name="prescriptions",
        record_id=prescription_id,
        new_data={"sold_at": str(updated.sold_at)},
        description=f"Xác nhận đã bán đơn {updated.prescription_code}",
    )
    await db.commit()
    return updated


# ── QR Code ───────────────────────────────────────────────────────────────────

@router.get(
    "/{prescription_id}/qr",
    summary="Sinh QR code tra cứu đơn thuốc",
    responses={
        200: {"content": {"image/png": {}}, "description": "QR code PNG"},
        404: {"description": "Không tìm thấy đơn thuốc"},
        409: {"description": "Đơn chưa được gửi thành công — chưa có mã để tra cứu"},
    },
)
async def get_qr_code(
    prescription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Tạo QR code PNG chứa URL tra cứu đơn thuốc trên hệ thống quốc gia.

    URL format: ``https://donthuocquocgia.vn/tra-cuu/{prescription_code}``

    Yêu cầu package ``qrcode[pil]``.

    Raises:
        HTTPException 409: Đơn chưa có mã (chưa gửi thành công).
    """
    obj = await _get_or_404(db, prescription_id)

    if not obj.prescription_code:
        raise HTTPException(
            status_code=409,
            detail="Đơn chưa có mã — không thể sinh QR code.",
        )

    lookup_url = (
        f"https://donthuocquocgia.vn/tra-cuu/{obj.prescription_code}"
    )

    try:
        import io
        import qrcode  # type: ignore[import]
        from qrcode.image.pil import PilImage  # type: ignore[import]

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(lookup_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="image/png",
            headers={
                "Content-Disposition": f'inline; filename="rx_{obj.prescription_code}.png"',
                "X-Prescription-Code": obj.prescription_code,
                "X-Lookup-URL": lookup_url,
            },
        )
    except ImportError:
        # Nếu chưa cài qrcode — trả plain text URL
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            content=lookup_url,
            media_type="text/plain",
            headers={"X-Lookup-URL": lookup_url},
        )
