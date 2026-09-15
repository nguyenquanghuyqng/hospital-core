"""
Doctor endpoints — giao diện dành riêng cho bác sĩ tại phòng khám.

Tất cả endpoints yêu cầu role ``doctor`` hoặc ``admin``
(dependency :func:`~app.core.deps.require_doctor`).

Tầng này chỉ chứa HTTP orchestration:
  - Parse request, resolve params.
  - Uỷ quyền toàn bộ business logic cho :class:`~app.services.doctor_service.DoctorService`.
  - Trả về DTO response.

Routes:
  GET    /doctor/queue                        — Danh sách BN chờ khám theo phòng
  GET    /doctor/queue/stats                  — Thống kê nhanh chờ / đã khám
  PATCH  /doctor/receptions/{id}/visit-status — Cập nhật trạng thái xử lý BN
  POST   /doctor/receptions/{id}/done         — Kết thúc khám (→ COMPLETED)
  PATCH  /doctor/receptions/{id}/transfer     — Chuyển BN sang phòng khám khác
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import require_doctor
from app.models.user import User
from app.schemas.doctor import (
    QueueItem,
    QueueStatsResponse,
    TransferRequest,
    VisitStatusUpdate,
)
from app.services.doctor_service import doctor_service

router = APIRouter(prefix="/doctor", tags=["Doctor - Phòng khám bác sĩ"])


# ── Danh sách chờ khám ────────────────────────────────────────────────────────

@router.get(
    "/queue",
    response_model=list[QueueItem],
    summary="Danh sách bệnh nhân chờ khám",
)
async def get_doctor_queue(
    clinic_room: Optional[str] = Query(
        None, description="Phòng khám; mặc định phòng của bác sĩ đăng nhập"
    ),
    visit_date: Optional[date] = Query(None, description="Ngày khám, mặc định hôm nay"),
    q: Optional[str] = Query(None, description="Từ khoá tìm kiếm trên thông tin bệnh nhân"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Trả về danh sách BN đang CHECKED_IN tại phòng, sắp xếp ưu tiên cao → số khám tăng.

    Args:
        clinic_room: Tên phòng khám (mặc định phòng của bác sĩ đăng nhập).
        visit_date: Ngày khám (mặc định hôm nay).
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        Danh sách :class:`~app.schemas.doctor.QueueItem`.
    """
    room = doctor_service.resolve_clinic_room(clinic_room, current_user.clinic_room)
    target_date = visit_date or date.today()
    return await doctor_service.get_queue(db, clinic_room=room, visit_date=target_date, q=q)


# ── Thống kê nhanh ────────────────────────────────────────────────────────────

@router.get(
    "/queue/stats",
    response_model=QueueStatsResponse,
    summary="Thống kê nhanh: chờ / đã khám theo phòng",
)
async def get_queue_stats(
    clinic_room: Optional[str] = Query(None),
    visit_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Đếm nhanh số BN theo từng ``visit_status`` tại phòng khám trong ngày.

    Args:
        clinic_room: Tên phòng khám (mặc định phòng của bác sĩ đăng nhập).
        visit_date: Ngày cần thống kê (mặc định hôm nay).
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        :class:`~app.schemas.doctor.QueueStatsResponse`.
    """
    room = doctor_service.resolve_clinic_room(clinic_room, current_user.clinic_room)
    target_date = visit_date or date.today()
    return await doctor_service.get_queue_stats(db, clinic_room=room, visit_date=target_date)


# ── Cập nhật trạng thái xử lý ─────────────────────────────────────────────────

@router.patch(
    "/receptions/{reception_id}/visit-status",
    response_model=QueueItem,
    summary="Cập nhật trạng thái xử lý bệnh nhân",
)
async def update_visit_status(
    reception_id: int,
    body: VisitStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Bác sĩ cập nhật trạng thái xử lý bệnh nhân trong quy trình khám.

    Các chuyển trạng thái thông thường::

        WAITING → CLS → CLS_RESULT → (REVISIT) → DONE

    Broadcast cập nhật real-time tới quầy tiếp đón sau khi thay đổi.

    Args:
        reception_id: ID lượt tiếp đón cần cập nhật.
        body: :class:`~app.schemas.doctor.VisitStatusUpdate` chứa trạng thái mới.
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        :class:`~app.schemas.doctor.QueueItem` đã cập nhật.

    Raises:
        HTTPException 404: Không tìm thấy lượt tiếp đón.
    """
    return await doctor_service.update_visit_status(
        db,
        reception_id=reception_id,
        body=body,
        updated_by=current_user.username,
    )


# ── Kết thúc khám ─────────────────────────────────────────────────────────────

@router.post(
    "/receptions/{reception_id}/done",
    response_model=QueueItem,
    summary="Kết thúc khám → COMPLETED",
)
async def complete_visit(
    reception_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Bác sĩ kết thúc lượt khám — chuyển Reception sang COMPLETED và VisitStatus → DONE.

    Idempotent: nếu đã COMPLETED thì trả về nguyên kết quả hiện có.

    Args:
        reception_id: ID lượt tiếp đón cần kết thúc.
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        :class:`~app.schemas.doctor.QueueItem` với status COMPLETED và visit_status DONE.

    Raises:
        HTTPException 404: Không tìm thấy lượt tiếp đón.
    """
    return await doctor_service.complete_visit(
        db,
        reception_id=reception_id,
        updated_by=current_user.username,
    )


# ── Chuyển khám ───────────────────────────────────────────────────────────────

@router.patch(
    "/receptions/{reception_id}/transfer",
    response_model=QueueItem,
    summary="Chuyển bệnh nhân sang phòng khám khác",
)
async def transfer_patient(
    reception_id: int,
    body: TransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Chuyển bệnh nhân sang phòng khám khác trong cùng cơ sở.

    Cập nhật ``clinic_room`` và reset ``visit_status`` về WAITING.
    Lý do chuyển phòng được append vào ``internal_note``.
    Broadcast tới cả phòng cũ và phòng mới.

    Args:
        reception_id: ID lượt tiếp đón cần chuyển phòng.
        body: :class:`~app.schemas.doctor.TransferRequest` chứa phòng đích và ghi chú.
        db: Async database session (injected).
        current_user: Bác sĩ / admin đang đăng nhập (injected).

    Returns:
        :class:`~app.schemas.doctor.QueueItem` đã được cập nhật với phòng mới.

    Raises:
        HTTPException 404: Không tìm thấy lượt tiếp đón.
    """
    return await doctor_service.transfer_patient(
        db,
        reception_id=reception_id,
        body=body,
        updated_by=current_user.username,
    )
