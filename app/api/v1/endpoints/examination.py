"""
Examination endpoints — phiếu khám bệnh.

Tất cả endpoints yêu cầu role ``doctor`` hoặc ``admin``
(dependency :func:`~app.core.deps.require_doctor`).

Routes:
  POST   /examinations                        — Tạo phiếu khám mới (idempotent)
  GET    /examinations/history/{patient_id}   — Lịch sử khám của bệnh nhân
  GET    /examinations/by-reception/{rid}     — Lấy phiếu theo reception_id
  GET    /examinations/{id}                   — Chi tiết phiếu khám
  PUT    /examinations/{id}                   — Cập nhật phiếu khám
  POST   /examinations/{id}/save              — Lưu tạm (DRAFT → SAVED)
  POST   /examinations/{id}/complete          — Kết thúc khám (→ COMPLETED)
  POST   /examinations/{id}/skip              — Bỏ qua bệnh nhân
  GET    /examinations/{id}/cost              — Tổng hợp chi phí
  POST   /examinations/{id}/diagnoses         — Thêm một chẩn đoán
  DELETE /examinations/{id}/diagnoses/{did}   — Xoá một chẩn đoán
  POST   /examinations/{id}/items             — Thêm kê đơn / CLS
  DELETE /examinations/{id}/items/{iid}       — Xoá kê đơn / CLS
"""
import logging
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


# ── Private helpers ────────────────────────────────────────────────────────────

async def _get_exam_or_404(db: AsyncSession, examination_id: int):
    """
    Lấy phiếu khám đầy đủ hoặc raise HTTP 404.

    Helper dùng chung cho các endpoint cần load phiếu khám trước khi xử lý.

    Args:
        db: Async database session.
        examination_id: ID phiếu khám cần lấy.

    Returns:
        :class:`~app.models.examination.Examination` với đầy đủ collection.

    Raises:
        HTTPException 404: Không tìm thấy phiếu khám.
    """
    exam = await crud_examination.get_full(db, examination_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu khám")
    return exam


def _assert_not_completed(exam) -> None:
    """
    Kiểm tra phiếu khám chưa hoàn tất để cho phép chỉnh sửa.

    Args:
        exam: Instance :class:`~app.models.examination.Examination` cần kiểm tra.

    Raises:
        HTTPException 400: Phiếu đã ở trạng thái COMPLETED — không thể chỉnh sửa.
    """
    if exam.status == ExaminationStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Phiếu đã kết thúc, không thể chỉnh sửa")


async def _assert_owns_diagnosis(
    db: AsyncSession, examination_id: int, diagnosis_id: int
) -> Diagnosis:
    """
    Kiểm tra chẩn đoán thuộc về phiếu khám được chỉ định.

    Ngăn bác sĩ xoá chẩn đoán của phiếu khám khác qua ID manipulation.

    Args:
        db: Async database session.
        examination_id: ID phiếu khám owner.
        diagnosis_id: ID chẩn đoán cần kiểm tra.

    Returns:
        :class:`~app.models.examination.Diagnosis` nếu hợp lệ.

    Raises:
        HTTPException 404: Chẩn đoán không tồn tại hoặc không thuộc phiếu này.
    """
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


async def _assert_owns_item(
    db: AsyncSession, examination_id: int, item_id: int
) -> PrescriptionItem:
    """
    Kiểm tra dòng kê đơn / CLS thuộc về phiếu khám được chỉ định.

    Ngăn bác sĩ xoá kê đơn của phiếu khám khác qua ID manipulation.

    Args:
        db: Async database session.
        examination_id: ID phiếu khám owner.
        item_id: ID dòng kê đơn cần kiểm tra.

    Returns:
        :class:`~app.models.examination.PrescriptionItem` nếu hợp lệ.

    Raises:
        HTTPException 404: Dòng kê đơn không tồn tại hoặc không thuộc phiếu này.
    """
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


async def _broadcast_queue_update(
    reception_id: int, visit_status: VisitStatus, clinic_room: str | None
) -> None:
    """
    Broadcast cập nhật trạng thái xử lý bệnh nhân tới quầy tiếp đón.

    Args:
        reception_id: ID lượt tiếp đón vừa thay đổi.
        visit_status: Trạng thái xử lý mới.
        clinic_room: Phòng khám liên quan (dùng để lọc phía client).
    """
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
    Bác sĩ bắt đầu khám bệnh nhân — tạo phiếu khám mới.

    Idempotent: nếu phiếu đã tồn tại cho reception này, trả về phiếu cũ.
    Tự điền ``doctor_id`` và ``doctor_name`` từ user đang đăng nhập nếu không truyền.
    Race-condition protected: ``IntegrityError`` được bắt và trả về phiếu đã tạo.

    Args:
        obj_in: :class:`~app.schemas.examination.ExaminationCreate`.
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        :class:`~app.schemas.examination.ExaminationResponse` đầy đủ.

    Raises:
        HTTPException 404: Không tìm thấy lượt tiếp đón.
        HTTPException 400: Lượt tiếp đón chưa ở trạng thái CHECKED_IN.
        HTTPException 500: Lỗi tạo phiếu không xác định.
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
    if not obj_in.patient_id:
        obj_in = obj_in.model_copy(update={"patient_id": reception.patient_id})
    if not obj_in.doctor_id:
        obj_in = obj_in.model_copy(update={"doctor_id": current_user.id})
    if not obj_in.doctor_name:
        obj_in = obj_in.model_copy(
            update={"doctor_name": current_user.full_name or current_user.username}
        )
    try:
        exam = await crud_examination.create_examination(db, obj_in=obj_in)
    except IntegrityError:
        # Concurrent request đã tạo record giữa check và insert
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
    """
    Lấy danh sách phiếu khám của một bệnh nhân, mới nhất trước.

    Kèm thông tin chẩn đoán tóm tắt để hiển thị trong danh sách lịch sử.

    Args:
        patient_id: ID bệnh nhân cần xem lịch sử.
        skip: Offset phân trang.
        limit: Số bản ghi tối đa (1–100).
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        Danh sách :class:`~app.schemas.examination.ExaminationList`.
    """
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
    """
    Lấy phiếu khám liên kết với một lượt tiếp đón cụ thể (quan hệ 1-1).

    Args:
        reception_id: ID lượt tiếp đón.
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        :class:`~app.schemas.examination.ExaminationResponse` đầy đủ.

    Raises:
        HTTPException 404: Chưa có phiếu khám cho lượt tiếp đón này.
    """
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
    """
    Lấy chi tiết đầy đủ một phiếu khám theo ID.

    Kèm danh sách chẩn đoán và kê đơn / CLS đã load sẵn.

    Args:
        examination_id: ID phiếu khám.
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        :class:`~app.schemas.examination.ExaminationResponse`.

    Raises:
        HTTPException 404: Không tìm thấy phiếu khám.
    """
    return await _get_exam_or_404(db, examination_id)


# ── Cập nhật ───────────────────────────────────────────────────────────────────

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
    """
    Cập nhật nội dung phiếu khám (partial update, chỉ DRAFT hoặc SAVED).

    Nếu ``diagnoses`` / ``prescription_items`` được truyền → replace-all collection.

    Args:
        examination_id: ID phiếu khám cần cập nhật.
        obj_in: :class:`~app.schemas.examination.ExaminationUpdate`.
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        :class:`~app.schemas.examination.ExaminationResponse` sau cập nhật.

    Raises:
        HTTPException 404: Không tìm thấy phiếu khám.
        HTTPException 400: Phiếu đã COMPLETED, không thể chỉnh sửa.
    """
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
    """
    Lưu tạm phiếu khám — bác sĩ có thể tiếp tục chỉnh sửa sau.

    Chuyển trạng thái DRAFT → SAVED.

    Args:
        examination_id: ID phiếu khám cần lưu.
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        :class:`~app.schemas.examination.ExaminationResponse` với status SAVED.

    Raises:
        HTTPException 404: Không tìm thấy phiếu khám.
        HTTPException 400: Phiếu đã COMPLETED.
    """
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
    Bác sĩ kết thúc khám — chuỗi thao tác nguyên tử:

    1. Examination → COMPLETED + ghi ``exam_end_at``.
    2. Reception   → COMPLETED + ghi ``completed_at``.
    3. VisitStatus → DONE.
    4. Broadcast cập nhật real-time tới quầy tiếp đón.

    Idempotent: phiếu đã COMPLETED thì trả về ngay không xử lý thêm.

    Args:
        examination_id: ID phiếu khám cần kết thúc.
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        :class:`~app.schemas.examination.ExaminationResponse` với status COMPLETED.

    Raises:
        HTTPException 404: Không tìm thấy phiếu khám.
    """
    exam = await _get_exam_or_404(db, examination_id)
    if exam.status == ExaminationStatus.COMPLETED:
        return exam

    completed = await crud_examination.complete_examination(db, db_obj=exam)

    # Uỷ quyền hoàn tất reception cho CRUD layer — không mutate trực tiếp tại đây
    reception = await crud_reception.get(db, exam.reception_id)
    if reception and reception.status != ReceptionStatus.COMPLETED:
        await crud_reception.complete_reception(db, reception=reception)
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
    """
    Bác sĩ bỏ qua bệnh nhân này — reset VisitStatus về WAITING để quay lại hàng đợi.

    Chỉ cho phép khi phiếu chưa COMPLETED.

    Args:
        examination_id: ID phiếu khám cần bỏ qua.
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        :class:`~app.schemas.examination.ExaminationResponse` (phiếu không thay đổi trạng thái).

    Raises:
        HTTPException 404: Không tìm thấy phiếu khám.
        HTTPException 400: Phiếu đã COMPLETED.
    """
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
    """
    Tính tổng chi phí real-time của phiếu khám.

    Phân loại: thuốc (drug_total), CLS (cls_total), tổng cộng,
    BHYT chi trả, và bệnh nhân cùng chi trả.

    Args:
        examination_id: ID phiếu khám cần tính chi phí.
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        :class:`~app.schemas.examination.CostSummary`.

    Raises:
        HTTPException 404: Không tìm thấy phiếu khám.
    """
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
    """
    Thêm một dòng chẩn đoán ICD-10 vào phiếu khám đang mở.

    ``sort_order`` tự tăng để giữ thứ tự thêm vào.

    Args:
        examination_id: ID phiếu khám cần thêm chẩn đoán.
        obj_in: :class:`~app.schemas.examination.DiagnosisCreate`.
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        :class:`~app.schemas.examination.DiagnosisResponse` vừa tạo.

    Raises:
        HTTPException 404: Không tìm thấy phiếu khám.
        HTTPException 400: Phiếu đã COMPLETED.
    """
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
    """
    Xoá một dòng chẩn đoán khỏi phiếu khám.

    Kiểm tra ownership (chẩn đoán phải thuộc phiếu này) trước khi xoá.

    Args:
        examination_id: ID phiếu khám owner.
        diagnosis_id: ID chẩn đoán cần xoá.
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Raises:
        HTTPException 404: Không tìm thấy phiếu khám hoặc chẩn đoán.
        HTTPException 400: Phiếu đã COMPLETED.
    """
    exam = await _get_exam_or_404(db, examination_id)
    _assert_not_completed(exam)
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
    """
    Thêm một dòng kê đơn thuốc hoặc chỉ định CLS vào phiếu khám đang mở.

    ``sort_order`` tự tăng; ``total_amount`` tự tính nếu có ``unit_price``.

    Args:
        examination_id: ID phiếu khám cần thêm kê đơn.
        obj_in: :class:`~app.schemas.examination.PrescriptionItemCreate`.
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        :class:`~app.schemas.examination.PrescriptionItemResponse` vừa tạo.

    Raises:
        HTTPException 404: Không tìm thấy phiếu khám.
        HTTPException 400: Phiếu đã COMPLETED.
    """
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
    """
    Xoá một dòng kê đơn / chỉ định CLS khỏi phiếu khám.

    Kiểm tra ownership trước khi xoá.

    Args:
        examination_id: ID phiếu khám owner.
        item_id: ID dòng kê đơn cần xoá.
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Raises:
        HTTPException 404: Không tìm thấy phiếu khám hoặc dòng kê đơn.
        HTTPException 400: Phiếu đã COMPLETED.
    """
    exam = await _get_exam_or_404(db, examination_id)
    _assert_not_completed(exam)
    await _assert_owns_item(db, examination_id, item_id)
    await crud_examination.delete_prescription_item(db, item_id=item_id)
