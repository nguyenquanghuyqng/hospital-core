"""
API endpoints cho hệ thống cấp số và gọi số thứ tự.

Routes:
  POST   /queue/ticket          — Bệnh nhân lấy số thứ tự
  GET    /queue/tickets         — Danh sách số thứ tự hôm nay
  GET    /queue/tickets/{id}    — Chi tiết một số thứ tự
  GET    /queue/summary         — Tóm tắt hàng đợi hôm nay
  GET    /queue/waiting         — Danh sách đang chờ
  POST   /queue/call-next       — Gọi số tiếp theo
  PATCH  /queue/tickets/{id}/status  — Cập nhật trạng thái thủ công
  PATCH  /queue/tickets/{id}/skip    — Bỏ qua số thứ tự
  PATCH  /queue/tickets/{id}/done    — Hoàn thành
  WS     /queue/ws/{room}       — WebSocket real-time
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


# ─────────────────────────────────────────────
#  WebSocket endpoint
# ─────────────────────────────────────────────
@router.websocket("/ws/{room}")
async def websocket_queue(websocket: WebSocket, room: str):
    """
    Kết nối WebSocket theo room:
    - **display**   : Màn hình LED hiển thị số đang gọi
    - **kiosk**     : Quầy lấy số / kiosk bệnh nhân
    - **reception** : Quầy tiếp đón nhân viên
    """
    if room not in ("display", "kiosk", "reception"):
        await websocket.close(code=4001, reason="Invalid room")
        return

    await ws_manager.connect(websocket, room=room)
    try:
        while True:
            # Giữ kết nối sống, client có thể gửi ping
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, room=room)


# ─────────────────────────────────────────────
#  REST endpoints
# ─────────────────────────────────────────────
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
    Tự động tạo ticket_number tăng dần trong ngày (A001, A002…).
    """
    ticket = await crud_queue_ticket.create_ticket(db, obj_in=obj_in)

    # Broadcast tới tất cả clients
    await ws_manager.broadcast_new_ticket({
        "id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "sequence": ticket.sequence,
        "service_type": ticket.service_type,
        "status": ticket.status,
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
    """Trả về thống kê số thứ tự theo ngày: tổng, chờ, đang gọi, phục vụ, xong, bỏ qua."""
    summary = await crud_queue_ticket.get_summary(db, issue_date=issue_date)
    return summary


@router.get(
    "/waiting",
    response_model=list[QueueTicketList],
    summary="Danh sách số đang chờ",
)
async def get_waiting_list(
    issue_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Trả về danh sách số thứ tự đang chờ (WAITING), sắp xếp theo sequence."""
    tickets = await crud_queue_ticket.get_waiting_list(db, issue_date=issue_date)
    return tickets


@router.get(
    "/tickets",
    response_model=list[QueueTicketList],
    summary="Danh sách số thứ tự theo ngày",
)
async def list_tickets(
    issue_date: Optional[date] = Query(None, description="Ngày, mặc định hôm nay"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    from app.models.queue_ticket import QueueStatus
    status_enum = None
    if status:
        try:
            status_enum = QueueStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Trạng thái không hợp lệ: {status}")

    tickets = await crud_queue_ticket.get_by_date(
        db,
        issue_date=issue_date or date.today(),
        status=status_enum,
        skip=skip,
        limit=limit,
    )
    return tickets


@router.get(
    "/tickets/{ticket_id}",
    response_model=QueueTicketResponse,
    summary="Chi tiết số thứ tự",
)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
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
    Nhân viên bấm **Gọi số tiếp theo**:
    - Số đang CALLING → SERVING
    - Số WAITING nhỏ nhất → CALLING
    - Broadcast lên màn hình LED qua WebSocket
    """
    ticket = await crud_queue_ticket.call_next(db)
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Không còn bệnh nhân nào trong hàng đợi",
        )
    if counter_number:
        ticket.counter_number = counter_number

    # Broadcast màn hình LED
    await ws_manager.broadcast_calling(
        ticket_number=ticket.ticket_number,
        counter_number=ticket.counter_number,
        patient_name=None,
    )
    # Cập nhật summary cho tất cả
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
    ticket = await crud_queue_ticket.get(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Không tìm thấy số thứ tự")

    ticket = await crud_queue_ticket.complete_ticket(db, ticket=ticket)
    summary = await crud_queue_ticket.get_summary(db)
    await ws_manager.broadcast_queue_update(summary)
    return ticket
