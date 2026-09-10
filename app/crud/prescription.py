"""
CRUD operations cho Prescription (đơn thuốc điện tử chuẩn BYT).

Các thao tác chính:
  create_for_examination — Tạo đơn tự động khi hoàn tất phiếu khám
  get_by_examination     — Lấy đơn theo examination_id
  get_full               — Lấy đơn với đầy đủ prescription_items
  update_push_status     — Cập nhật trạng thái đẩy (gọi bởi NationalPrescriptionService)
  get_pending_retry      — Lấy danh sách đơn cần retry
  dashboard_stats        — Thống kê tỷ lệ thành công cho admin dashboard
"""
import json
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.prescription import Prescription
from app.models.examination import PrescriptionItem
from app.models.catalog import Drug
from app.models.enums import PrescriptionPushStatus, PrescriptionType, DrugCategory
from app.schemas.prescription import (
    PrescriptionCreate, PrescriptionUpdate, PrescriptionDashboard,
)
from app.services.prescription_code import generate_prescription_code, classify_prescription_type

logger = logging.getLogger(__name__)

_MAX_RETRY = 5
_RETRY_DELAYS = [5, 15, 30, 60, 120]  # phút, tăng dần theo số lần retry


class CRUDPrescription:
    """
    CRUD layer cho bảng ``prescriptions``.

    Không kế thừa :class:`~app.crud.base.CRUDBase` vì logic tạo đơn
    phức tạp hơn (cần đọc items + sinh mã + validate).
    """

    async def _load_drug_categories(
        self, db: AsyncSession, examination_id: int
    ) -> list[str]:
        """
        Lấy danh sách drug_category của tất cả PrescriptionItem (item_type='drug')
        trong một phiếu khám. Dùng để phân loại đơn N/H/C.
        """
        result = await db.execute(
            select(Drug.drug_category)
            .join(
                PrescriptionItem,
                and_(
                    PrescriptionItem.item_code == Drug.drug_code,
                    PrescriptionItem.item_type == "drug",
                    PrescriptionItem.examination_id == examination_id,
                )
            )
        )
        return [row[0].value for row in result.all() if row[0]]

    async def create_for_examination(
        self,
        db: AsyncSession,
        data: PrescriptionCreate,
        facility_code: str,
    ) -> Prescription:
        """
        Tạo đơn thuốc mới cho một phiếu khám đã hoàn tất.

        Tự động:
        - Phân loại đơn N/H/C dựa trên danh mục thuốc kê.
        - Sinh mã đơn 14 ký tự duy nhất.
        - Gán push_status = PENDING.

        Args:
            db: Async database session.
            data: :class:`~app.schemas.prescription.PrescriptionCreate`.
            facility_code: 5 ký tự mã cơ sở từ system_config.

        Returns:
            :class:`~app.models.prescription.Prescription` đã flush vào session.
        """
        # Phân loại đơn
        drug_cats = await self._load_drug_categories(db, data.examination_id)
        p_type_str = classify_prescription_type(drug_cats)
        p_type = PrescriptionType(p_type_str)

        # Sinh mã đơn
        code = await generate_prescription_code(db, facility_code, p_type_str)

        obj = Prescription(
            examination_id      = data.examination_id,
            patient_id          = data.patient_id,
            doctor_id           = data.doctor_id,
            prescription_code   = code,
            facility_code       = facility_code[:5].upper(),
            prescription_type   = p_type,
            push_status         = PrescriptionPushStatus.PENDING,
            is_inpatient        = data.is_inpatient,
            treatment_from      = data.treatment_from,
            treatment_to        = data.treatment_to,
            patient_phone       = data.patient_phone,
            patient_weight_kg   = data.patient_weight_kg,
            patient_gender_code = data.patient_gender_code,
            guardian_name       = data.guardian_name,
            recipient_cccd      = data.recipient_cccd,
            recipient_name      = data.recipient_name,
            doctor_name         = data.doctor_name,
            doctor_national_code= data.doctor_national_code,
        )
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def get_by_examination(
        self, db: AsyncSession, examination_id: int
    ) -> Optional[Prescription]:
        """Lấy đơn theo examination_id."""
        result = await db.execute(
            select(Prescription).where(Prescription.examination_id == examination_id)
        )
        return result.scalar_one_or_none()

    async def get_full(
        self, db: AsyncSession, prescription_id: int
    ) -> Optional[Prescription]:
        """Lấy đơn đầy đủ với prescription_items."""
        result = await db.execute(
            select(Prescription)
            .options(
                selectinload(Prescription.prescription_items),
            )
            .where(Prescription.id == prescription_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        db: AsyncSession,
        obj: Prescription,
        data: PrescriptionUpdate,
    ) -> Prescription:
        """
        Cập nhật thông tin phụ trợ của đơn thuốc (không cho sửa mã đơn đã gửi).

        Args:
            db: Async database session.
            obj: Instance Prescription cần cập nhật.
            data: PrescriptionUpdate với các fields cần thay đổi.

        Raises:
            ValueError: Đơn đã gửi thành công không được phép sửa.
        """
        if obj.push_status == PrescriptionPushStatus.SUCCESS:
            raise ValueError("Đơn đã gửi thành công lên hệ thống quốc gia, không thể chỉnh sửa.")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(obj, field, value)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def update_push_status(
        self,
        db: AsyncSession,
        obj: Prescription,
        status: PrescriptionPushStatus,
        national_ref_id: Optional[str] = None,
        error_info: Optional[dict] = None,
    ) -> Prescription:
        """
        Cập nhật trạng thái đẩy đơn sau khi gọi API BYT.

        Khi thành công: gán sent_at, national_ref_id.
        Khi lỗi: tăng retry_count, tính retry_at, ghi error_log.

        Args:
            db: Async database session.
            obj: Prescription instance cần cập nhật.
            status: Trạng thái mới.
            national_ref_id: ID đơn từ BYT (khi thành công).
            error_info: Dict thông tin lỗi (khi thất bại).
        """
        obj.push_status = status
        now = datetime.now(timezone.utc)

        if status == PrescriptionPushStatus.SUCCESS:
            obj.sent_at = now
            if national_ref_id:
                obj.national_ref_id = national_ref_id
            obj.error_log = None

        elif status == PrescriptionPushStatus.ERROR:
            obj.retry_count = (obj.retry_count or 0) + 1
            if error_info:
                obj.error_log = json.dumps(
                    {"attempt": obj.retry_count, "at": now.isoformat(), **error_info},
                    ensure_ascii=False,
                )
            # Tính delay retry theo backoff
            delay_idx = min(obj.retry_count - 1, len(_RETRY_DELAYS) - 1)
            obj.retry_at = now + timedelta(minutes=_RETRY_DELAYS[delay_idx])

        await db.flush()
        await db.refresh(obj)
        return obj

    async def mark_sold(
        self, db: AsyncSession, obj: Prescription
    ) -> Prescription:
        """Đánh dấu đơn đã được bán (đồng bộ từ nhà thuốc)."""
        obj.sold_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def get_pending_retry(
        self, db: AsyncSession, max_retry: int = _MAX_RETRY
    ) -> List[Prescription]:
        """
        Lấy danh sách đơn cần retry: status=ERROR, retry_count < max_retry,
        retry_at <= now.

        Args:
            db: Async database session.
            max_retry: Giới hạn số lần retry tối đa.

        Returns:
            List Prescription cần retry, sắp xếp theo retry_at tăng dần.
        """
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Prescription)
            .where(
                and_(
                    Prescription.push_status == PrescriptionPushStatus.ERROR,
                    Prescription.retry_count < max_retry,
                    Prescription.retry_at <= now,
                    Prescription.is_inpatient == False,  # noqa: E712
                )
            )
            .order_by(Prescription.retry_at.asc())
            .limit(50)
        )
        return list(result.scalars().all())

    async def dashboard_stats(
        self, db: AsyncSession, facility_code: Optional[str] = None
    ) -> PrescriptionDashboard:
        """
        Thống kê tổng hợp để hiển thị dashboard giám sát liên thông.

        Tính theo ngày hôm nay (00:00 → 23:59 local).
        """
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
        today_end   = today_start + timedelta(days=1)

        today_filter = and_(
            Prescription.created_at >= today_start,
            Prescription.created_at < today_end,
        )

        # Tổng hôm nay
        total_q = await db.execute(
            select(func.count(Prescription.id)).where(today_filter)
        )
        total_today = total_q.scalar() or 0

        # Group by status hôm nay
        status_q = await db.execute(
            select(
                Prescription.push_status,
                func.count(Prescription.id).label("cnt"),
            )
            .where(today_filter)
            .group_by(Prescription.push_status)
        )
        status_counts = {row[0].value: row[1] for row in status_q.all()}

        # Avg retry
        avg_q = await db.execute(
            select(func.avg(Prescription.retry_count)).where(today_filter)
        )
        avg_retry = float(avg_q.scalar() or 0)

        # Last success
        last_q = await db.execute(
            select(func.max(Prescription.sent_at))
        )
        last_success_at = last_q.scalar()

        success_count = status_counts.get("success", 0)
        success_rate = (success_count / total_today * 100) if total_today > 0 else 0.0

        return PrescriptionDashboard(
            total_today     = total_today,
            pending         = status_counts.get("pending", 0) + status_counts.get("sending", 0),
            success         = success_count,
            error           = status_counts.get("error", 0),
            cancelled       = status_counts.get("cancelled", 0),
            success_rate_pct= round(success_rate, 1),
            avg_retry_count = round(avg_retry, 2),
            last_success_at = last_success_at,
            facility_code   = facility_code,
            is_facility_code_configured = bool(facility_code),
        )


crud_prescription = CRUDPrescription()
