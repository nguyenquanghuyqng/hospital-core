"""
Examination endpoints — phiếu khám bệnh.

Routes:
  POST   /examinations                        — Tạo phiếu khám mới
  GET    /examinations/history/{patient_id}   — Lịch sử khám
  GET    /examinations/by-reception/{rid}     — Lấy phiếu theo reception_id
  GET    /examinations/{id}                   — Chi tiết
  PUT    /examinations/{id}                   — Cập nhật
  POST   /examinations/{id}/save              — Lưu (DRAFT → SAVED)
  POST   /examinations/{id}/complete          — Kết thúc
  POST   /examinations/{id}/skip              — Bỏ qua BN
  GET    /examinations/{id}/cost              — Tổng chi phí
  POST   /examinations/{id}/diagnoses         — Thêm chẩn đoán
  DELETE /examinations/{id}/diagnoses/{did}   — Xoá chẩn đoán
  POST   /examinations/{id}/items             — Thêm kê đơn / CLS
  DELETE /examinations/{id}/items/{iid}       — Xoá kê đơn / CLS
"""
import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import require_doctor
from app.models.user import User
from app.models.examination import Diagnosis, PrescriptionItem
from app.models.enums import ExaminationStatus, ReceptionStatus, VisitStatus
from app.crud.examination import crud_examination
from app.crud.reception import crud_reception
from app.schemas.examination import (
    ExaminationCreate, ExaminationUpdate, ExaminationResponse,
    ExaminationList, CostSummary,
    DiagnosisCreate, DiagnosisResponse,
    PrescriptionItemCreate, PrescriptionItemResponse,
)
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/examinations", tags=["Examination - Phiếu khám"])


# ── Helpers ────────────────────────────────────────────────────────────────────
async def _get_exam_or_404(db: AsyncSession, examination_id: int):
    exam = await crud_examination.get_full(db, examination_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu khám")
    return exam


def _assert_not_completed(exam) -> None:
    if exam.status == ExaminationStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Phiếu đã kết thúc, không thể chỉnh sửa")


async def _assert_owns_diagnosis(db: AsyncSession, examination_id: int, diagnosis_id: int) -> Diagnosis:
    result = await db.execute(
        select(Diagnosis).where(
            Diagnosis.id == diagnosis_id,
            Diagnosis.examination_id == examination_id,
        )
    )
    diag = result.scalar_one_or_none()
    if not diag:
        raise HTTPException(status_code=404, detail="Không tìm thấy chẩn đoán trong phiếu này")
    return diag


async def _assert_owns_item(db: AsyncSession, examination_id: int, item_id: int) -> PrescriptionItem:
    result = await db.execute(
        select(PrescriptionItem).where(
            PrescriptionItem.id == item_id,
            PrescriptionItem.examination_id == examination_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy chỉ định trong phiếu này")
    return item


async def _broadcast_queue_update(reception_id: int, visit_status: VisitStatus, clinic_room: str | None) -> None:
    await ws_manager.broadcast("reception", {
        "type": "doctor_queue_update",
        "data": {
            "reception_id": reception_id,
            "visit_status": visit_status.value,
            "clinic_room":  clinic_room,
        },
    })


# ── Tạo mới ────────────────────────────────────────────────────────────────────
@router.post(
    "",
    response_model=ExaminationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo phiếu khám mới",
)
async def create_examination(
    obj_in: ExaminationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Bác sĩ bắt đầu khám bệnh nhân. Idempotent:
    - Nếu phiếu đã tồn tại cho reception này → trả về phiếu cũ.
    - Race-condition protected: IntegrityError → trả về phiếu đã tạo.
    """
    reception = await crud_reception.get(db, obj_in.reception_id)
    if not reception:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt tiếp đón")
    if reception.status != ReceptionStatus.CHECKED_IN:
        raise HTTPException(
            status_code=400,
            detail=f"Lượt tiếp đón phải ở trạng thái checked_in (hiện: {reception.status.value})",
        )

    # Idempotency: trả về phiếu đã có
    existing = await crud_examination.get_by_reception(db, obj_in.reception_id)
    if existing:
        return existing

    # Bổ sung thông tin bác sĩ từ user đang đăng nhập
    if not obj_in.doctor_id:
        obj_in = obj_in.model_copy(update={"doctor_id": current_user.id})
    if not obj_in.doctor_name:
        obj_in = obj_in.model_copy(
            update={"doctor_name": current_user.full_name or current_user.username}
        )

    try:
        exam = await crud_examination.create_examination(db, obj_in=obj_in)
    except IntegrityError:
        # Concurrent request created the record between our check and insert
        await db.rollback()
        exam = await crud_examination.get_by_reception(db, obj_in.reception_id)
        if not exam:
            raise HTTPException(status_code=500, detail="Lỗi tạo phiếu khám")

    return exam


# ── Tra cứu ────────────────────────────────────────────────────────────────────
@router.get(
    "/history/{patient_id}",
    response_model=List[ExaminationList],
    summary="Lịch sử khám của bệnh nhân",
)
async def get_history(
    patient_id: int,
    skip:  int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    return await crud_examination.get_history(db, patient_id, skip=skip, limit=limit)


@router.get(
    "/by-reception/{reception_id}",
    response_model=ExaminationResponse,
    summary="Lấy phiếu khám theo reception_id",
)
async def get_by_reception(
    reception_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    exam = await crud_examination.get_by_reception(db, reception_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Chưa có phiếu khám cho lượt tiếp đón này")
    return exam


@router.get(
    "/{examination_id}",
    response_model=ExaminationResponse,
    summary="Chi tiết phiếu khám",
)
async def get_examination(
    examination_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    return await _get_exam_or_404(db, examination_id)


# ── Cập nhật ────────────────────────────────────────────────────────────────────
@router.put(
    "/{examination_id}",
    response_model=ExaminationResponse,
    summary="Cập nhật phiếu khám",
)
async def update_examination(
    examination_id: int,
    obj_in: ExaminationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    exam = await _get_exam_or_404(db, examination_id)
    _assert_not_completed(exam)
    return await crud_examination.update_examination(db, db_obj=exam, obj_in=obj_in)


# ── Workflow transitions ────────────────────────────────────────────────────────
@router.post(
    "/{examination_id}/save",
    response_model=ExaminationResponse,
    summary="Lưu phiếu khám (DRAFT → SAVED)",
)
async def save_examination(
    examination_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    exam = await _get_exam_or_404(db, examination_id)
    _assert_not_completed(exam)
    return await crud_examination.save_examination(db, db_obj=exam)


@router.post(
    "/{examination_id}/complete",
    response_model=ExaminationResponse,
    summary="Kết thúc khám (→ COMPLETED)",
)
async def complete_examination(
    examination_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Luồng:
    1. Examination → COMPLETED + exam_end_at
    2. Reception   → COMPLETED
    3. VisitStatus → DONE
    """
    exam = await _get_exam_or_404(db, examination_id)
    if exam.status == ExaminationStatus.COMPLETED:
        return exam

    completed = await crud_examination.complete_examination(db, db_obj=exam)

    reception = await crud_reception.get(db, exam.reception_id)
    if reception and reception.status != ReceptionStatus.COMPLETED:
        reception.status       = ReceptionStatus.COMPLETED
        reception.visit_status = VisitStatus.DONE
        reception.completed_at = datetime.now(timezone.utc)
        db.add(reception)
        await db.flush()
        await _broadcast_queue_update(reception.id, VisitStatus.DONE, reception.clinic_room)

    return completed


@router.post(
    "/{examination_id}/skip",
    response_model=ExaminationResponse,
    summary="Bỏ qua bệnh nhân — trả về hàng đợi",
)
async def skip_examination(
    examination_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """Chỉ cho phép bỏ qua khi phiếu chưa hoàn tất."""
    exam = await _get_exam_or_404(db, examination_id)
    _assert_not_completed(exam)

    reception = await crud_reception.get(db, exam.reception_id)
    if reception and reception.visit_status != VisitStatus.DONE:
        reception.visit_status = VisitStatus.WAITING
        db.add(reception)
        await db.flush()
        await _broadcast_queue_update(reception.id, VisitStatus.WAITING, reception.clinic_room)

    return exam


# ── Chi phí ────────────────────────────────────────────────────────────────────
@router.get(
    "/{examination_id}/cost",
    response_model=CostSummary,
    summary="Tổng hợp chi phí",
)
async def get_cost(
    examination_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    await _get_exam_or_404(db, examination_id)
    return await crud_examination.get_cost_summary(db, examination_id)


# ── Diagnoses ──────────────────────────────────────────────────────────────────
@router.post(
    "/{examination_id}/diagnoses",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm chẩn đoán",
)
async def add_diagnosis(
    examination_id: int,
    obj_in: DiagnosisCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    exam = await _get_exam_or_404(db, examination_id)
    _assert_not_completed(exam)
    return await crud_examination.add_diagnosis(db, examination_id=examination_id, obj_in=obj_in)


@router.delete(
    "/{examination_id}/diagnoses/{diagnosis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá chẩn đoán",
)
async def delete_diagnosis(
    examination_id: int,
    diagnosis_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    exam = await _get_exam_or_404(db, examination_id)
    _assert_not_completed(exam)
    # Ownership: verify diagnosis belongs to this examination
    await _assert_owns_diagnosis(db, examination_id, diagnosis_id)
    await crud_examination.delete_diagnosis(db, diagnosis_id=diagnosis_id)


# ── Prescription items ─────────────────────────────────────────────────────────
@router.post(
    "/{examination_id}/items",
    response_model=PrescriptionItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm kê đơn / chỉ định CLS",
)
async def add_item(
    examination_id: int,
    obj_in: PrescriptionItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    exam = await _get_exam_or_404(db, examination_id)
    _assert_not_completed(exam)
    return await crud_examination.add_prescription_item(
        db, examination_id=examination_id, obj_in=obj_in
    )


@router.delete(
    "/{examination_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá kê đơn / CLS",
)
async def delete_item(
    examination_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    exam = await _get_exam_or_404(db, examination_id)
    _assert_not_completed(exam)
    # Ownership: verify item belongs to this examination
    await _assert_owns_item(db, examination_id, item_id)
    await crud_examination.delete_prescription_item(db, item_id=item_id)
