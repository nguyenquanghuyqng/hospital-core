"""
API endpoints cho hệ thống cấp số và gọi số thứ tự.

Routes:
  WS     /queue/ws/{room}              — Kết nối WebSocket real-time theo room
  POST   /queue/ticket                 — Bệnh nhân lấy số thứ tự mới
  GET    /queue/summary                — Tóm tắt hàng đợi hôm nay
  GET    /queue/waiting                — Danh sách số đang chờ
  GET    /queue/tickets                — Danh sách số theo ngày / trạng thái
  GET    /queue/tickets/{id}           — Chi tiết một số thứ tự
  POST   /queue/call-next              — Gọi số tiếp theo
  PATCH  /queue/tickets/{id}/status    — Cập nhật trạng thái thủ công
  PATCH  /queue/tickets/{id}/skip      — Bỏ qua số thứ tự
  PATCH  /queue/tickets/{id}/done      — Hoàn thành số thứ tự
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.crud.queue_ticket import crud_queue_ticket
from app.schemas.queue_ticket import (
    QueueTicketCreate, QueueTicketResponse, QueueTicketList,
    QueueTicketStatusUpdate, QueueSummary,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/queue", tags=["Queue - Hệ thống số thứ tự"])
logger = logging.getLogger(__name__)


# ── WebSocket ─────────────────────────────────────────────────────────────────

@router.websocket("/ws/{room}")
async def websocket_queue(websocket: WebSocket, room: str):
    """
    Kết nối WebSocket real-time theo room.

    Room hợp lệ:
    - ``display``   : Màn hình LED hiển thị số đang gọi (công khai).
    - ``kiosk``     : Quầy / kiosk lấy số thứ tự của bệnh nhân.
    - ``reception`` : Giao diện quầy tiếp đón dành cho nhân viên.

    Kết nối bị từ chối với code ``4001`` nếu ``room`` không hợp lệ.
    Client có thể gửi text ``"ping"`` để giữ kết nối; server trả lời ``"pong"``.

    Args:
        websocket: WebSocket connection từ client.
        room: Tên room cần tham gia.
    """
    if room not in ("display", "kiosk", "reception"):
        await websocket.close(code=4001, reason="Invalid room")
        return

    await ws_manager.connect(websocket, room=room)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, room=room)


# ── REST endpoints ────────────────────────────────────────────────────────────

@router.post(
    "/ticket",
    response_model=QueueTicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Lấy số thứ tự mới",
)
async def take_ticket(
    obj_in: QueueTicketCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Bệnh nhân bấm lấy số thứ tự tại kiosk hoặc quầy tiếp đón.

    Tạo số thứ tự mới với ``ticket_number`` tự tăng trong ngày (A001, A002…).
    Sau khi tạo, broadcast thông tin số mới tới tất cả clients qua WebSocket.

    Args:
        obj_in: :class:`~app.schemas.queue_ticket.QueueTicketCreate`.
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.queue_ticket.QueueTicketResponse` của số vừa cấp.
    """
    ticket = await crud_queue_ticket.create_ticket(db, obj_in=obj_in)
    await ws_manager.broadcast_new_ticket({
        "id":           ticket.id,
        "ticket_number": ticket.ticket_number,
        "sequence":     ticket.sequence,
        "service_type": ticket.service_type,
        "status":       ticket.status,
    })
    return ticket


@router.get(
    "/summary",
    response_model=QueueSummary,
    summary="Tóm tắt hàng đợi hôm nay",
)
async def get_queue_summary(
    issue_date: Optional[date] = Query(None, description="Ngày cần xem, mặc định hôm nay"),
    db: AsyncSession = Depends(get_db),
):
    """
    Trả về thống kê số thứ tự theo ngày: tổng, chờ, đang gọi, phục vụ, xong, bỏ qua.

    Dùng cho dashboard real-time và broadcast khi hàng đợi thay đổi.

    Args:
        issue_date: Ngày cần xem (mặc định hôm nay).
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.queue_ticket.QueueSummary`.
    """
    return await crud_queue_ticket.get_summary(db, issue_date=issue_date)


@router.get(
    "/waiting",
    response_model=list[QueueTicketList],
    summary="Danh sách số đang chờ",
)
async def get_waiting_list(
    issue_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Trả về danh sách số thứ tự đang chờ (WAITING), sắp xếp theo sequence tăng dần.

    Args:
        issue_date: Ngày cần xem (mặc định hôm nay).
        db: Async database session (injected).

    Returns:
        Danh sách :class:`~app.schemas.queue_ticket.QueueTicketList`.
    """
    return await crud_queue_ticket.get_waiting_list(db, issue_date=issue_date)


@router.get(
    "/tickets",
    response_model=list[QueueTicketList],
    summary="Danh sách số thứ tự theo ngày",
)
async def list_tickets(
    issue_date: Optional[date] = Query(None, description="Ngày, mặc định hôm nay"),
    status:     Optional[str]  = Query(None, description="Lọc theo trạng thái"),
    skip:  int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy danh sách số thứ tự theo ngày, tuỳ chọn lọc theo trạng thái.

    Args:
        issue_date: Ngày cần xem (mặc định hôm nay).
        status: Tên trạng thái cần lọc (VD: ``"waiting"``, ``"done"``).
        skip: Offset phân trang.
        limit: Số bản ghi tối đa (tối đa 200).
        db: Async database session (injected).

    Returns:
        Danh sách :class:`~app.schemas.queue_ticket.QueueTicketList`.

    Raises:
        HTTPException 400: Giá trị ``status`` không hợp lệ.
    """
    from app.models.queue_ticket import QueueStatus
    status_enum = None
    if status:
        try:
            status_enum = QueueStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Trạng thái không hợp lệ: {status}")

    return await crud_queue_ticket.get_by_date(
        db,
        issue_date=issue_date or date.today(),
        status=status_enum,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/tickets/{ticket_id}",
    response_model=QueueTicketResponse,
    summary="Chi tiết số thứ tự",
)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy thông tin chi tiết của một số thứ tự theo ID.

    Args:
        ticket_id: ID số thứ tự.
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.queue_ticket.QueueTicketResponse`.

    Raises:
        HTTPException 404: Không tìm thấy số thứ tự.
    """
    ticket = await crud_queue_ticket.get(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Không tìm thấy số thứ tự")
    return ticket


@router.post(
    "/call-next",
    response_model=QueueTicketResponse,
    summary="Gọi số thứ tự tiếp theo",
)
async def call_next(
    counter_number: Optional[int] = Query(None, ge=1, description="Số quầy đang gọi"),
    db: AsyncSession = Depends(get_db),
):
    """
    Nhân viên bấm gọi số tiếp theo trong hàng đợi.

    Thực hiện hai bước nguyên tử:
    1. Số đang CALLING → SERVING.
    2. Số WAITING nhỏ nhất → CALLING.

    Sau đó broadcast số đang gọi lên màn hình LED và cập nhật summary
    cho tất cả clients.

    Args:
        counter_number: Số quầy đang gọi (tuỳ chọn, gán vào ticket nếu cung cấp).
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.queue_ticket.QueueTicketResponse` của số vừa được gọi.

    Raises:
        HTTPException 404: Hàng đợi trống, không còn số nào đang chờ.
    """
    ticket = await crud_queue_ticket.call_next(db)
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Không còn bệnh nhân nào trong hàng đợi",
        )
    if counter_number:
        ticket.counter_number = counter_number

    await ws_manager.broadcast_calling(
        ticket_number=ticket.ticket_number,
        counter_number=ticket.counter_number,
        patient_name=None,
    )
    summary = await crud_queue_ticket.get_summary(db)
    await ws_manager.broadcast_queue_update(summary)
    return ticket


@router.patch(
    "/tickets/{ticket_id}/status",
    response_model=QueueTicketResponse,
    summary="Cập nhật trạng thái số thứ tự",
)
async def update_ticket_status(
    ticket_id: int,
    obj_in: QueueTicketStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Cập nhật trạng thái số thứ tự thủ công và broadcast summary mới.

    Timestamp tương ứng (called_at, served_at, done_at) được tự động ghi.

    Args:
        ticket_id: ID số thứ tự cần cập nhật.
        obj_in: :class:`~app.schemas.queue_ticket.QueueTicketStatusUpdate`.
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.queue_ticket.QueueTicketResponse` đã cập nhật.

    Raises:
        HTTPException 404: Không tìm thấy số thứ tự.
    """
    ticket = await crud_queue_ticket.get(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Không tìm thấy số thứ tự")

    ticket = await crud_queue_ticket.update_status(db, ticket=ticket, obj_in=obj_in)
    summary = await crud_queue_ticket.get_summary(db)
    await ws_manager.broadcast_queue_update(summary)
    return ticket


@router.patch(
    "/tickets/{ticket_id}/skip",
    response_model=QueueTicketResponse,
    summary="Bỏ qua số thứ tự (không có mặt)",
)
async def skip_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Đánh dấu số thứ tự là SKIPPED (gọi không có mặt) và broadcast summary.

    Args:
        ticket_id: ID số thứ tự cần bỏ qua.
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.queue_ticket.QueueTicketResponse` với status SKIPPED.

    Raises:
        HTTPException 404: Không tìm thấy số thứ tự.
    """
    ticket = await crud_queue_ticket.get(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Không tìm thấy số thứ tự")

    ticket = await crud_queue_ticket.skip_ticket(db, ticket=ticket)
    summary = await crud_queue_ticket.get_summary(db)
    await ws_manager.broadcast_queue_update(summary)
    return ticket


@router.patch(
    "/tickets/{ticket_id}/done",
    response_model=QueueTicketResponse,
    summary="Hoàn thành số thứ tự",
)
async def complete_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Đánh dấu số thứ tự là DONE (hoàn thành) và broadcast summary.

    Args:
        ticket_id: ID số thứ tự cần hoàn thành.
        db: Async database session (injected).

    Returns:
        :class:`~app.schemas.queue_ticket.QueueTicketResponse` với status DONE.

    Raises:
        HTTPException 404: Không tìm thấy số thứ tự.
    """
    ticket = await crud_queue_ticket.get(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Không tìm thấy số thứ tự")

    ticket = await crud_queue_ticket.complete_ticket(db, ticket=ticket)
    summary = await crud_queue_ticket.get_summary(db)
    await ws_manager.broadcast_queue_update(summary)
    return ticket
