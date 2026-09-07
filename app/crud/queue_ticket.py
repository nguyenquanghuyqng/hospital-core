from datetime import date, datetime, timezone
from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.queue_ticket import QueueTicket, QueueStatus
from app.schemas.queue_ticket import QueueTicketCreate, QueueTicketStatusUpdate


class CRUDQueueTicket(CRUDBase[QueueTicket]):

    # ------------------------------------------------------------------ #
    #  Tạo số thứ tự mới
    # ------------------------------------------------------------------ #
    async def create_ticket(
        self,
        db: AsyncSession,
        *,
        obj_in: QueueTicketCreate,
        issue_date: Optional[date] = None,
        prefix: str = "A",
    ) -> QueueTicket:
        """
        Tạo số thứ tự mới cho ngày hiện tại.
        Sequence tự tăng theo ngày, ticket_number = prefix + sequence 3 chữ số (A001…).
        """
        today = issue_date or date.today()

        # Lấy sequence tiếp theo trong ngày
        result = await db.execute(
            select(func.max(QueueTicket.sequence)).where(
                QueueTicket.issue_date == today
            )
        )
        max_seq: Optional[int] = result.scalar_one_or_none()
        next_seq = (max_seq or 0) + 1
        ticket_number = f"{prefix}{next_seq:03d}"

        ticket = QueueTicket(
            ticket_number=ticket_number,
            sequence=next_seq,
            issue_date=today,
            status=QueueStatus.WAITING,
            service_type=obj_in.service_type,
            note=obj_in.note,
        )
        db.add(ticket)
        await db.flush()
        await db.refresh(ticket)
        return ticket

    # ------------------------------------------------------------------ #
    #  Truy vấn
    # ------------------------------------------------------------------ #
    async def get_by_date(
        self,
        db: AsyncSession,
        *,
        issue_date: date,
        status: Optional[QueueStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[QueueTicket]:
        """Lấy danh sách số thứ tự theo ngày, tuỳ chọn lọc theo status."""
        query = select(QueueTicket).where(QueueTicket.issue_date == issue_date)
        if status:
            query = query.where(QueueTicket.status == status)
        query = query.order_by(QueueTicket.sequence).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_waiting_list(
        self, db: AsyncSession, *, issue_date: Optional[date] = None
    ) -> List[QueueTicket]:
        """Danh sách đang chờ (WAITING) hôm nay, sắp xếp theo sequence."""
        today = issue_date or date.today()
        return await self.get_by_date(db, issue_date=today, status=QueueStatus.WAITING, limit=200)

    async def get_current_calling(
        self, db: AsyncSession, *, issue_date: Optional[date] = None
    ) -> Optional[QueueTicket]:
        """Số thứ tự đang được gọi (CALLING)."""
        today = issue_date or date.today()
        result = await db.execute(
            select(QueueTicket)
            .where(
                and_(
                    QueueTicket.issue_date == today,
                    QueueTicket.status == QueueStatus.CALLING,
                )
            )
            .order_by(QueueTicket.called_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_summary(self, db: AsyncSession, *, issue_date: Optional[date] = None) -> dict:
        """Đếm số lượng theo từng trạng thái trong ngày."""
        today = issue_date or date.today()
        result = await db.execute(
            select(QueueTicket.status, func.count(QueueTicket.id))
            .where(QueueTicket.issue_date == today)
            .group_by(QueueTicket.status)
        )
        rows = result.all()
        counts = {r[0]: r[1] for r in rows}
        total = sum(counts.values())

        current = await self.get_current_calling(db, issue_date=today)
        return {
            "issue_date": today,
            "total": total,
            "waiting": counts.get(QueueStatus.WAITING, 0),
            "calling": counts.get(QueueStatus.CALLING, 0),
            "serving": counts.get(QueueStatus.SERVING, 0),
            "done": counts.get(QueueStatus.DONE, 0),
            "skipped": counts.get(QueueStatus.SKIPPED, 0),
            "current_calling": current.ticket_number if current else None,
        }

    # ------------------------------------------------------------------ #
    #  Cập nhật trạng thái
    # ------------------------------------------------------------------ #
    async def call_next(
        self, db: AsyncSession, *, issue_date: Optional[date] = None
    ) -> Optional[QueueTicket]:
        """
        Gọi số tiếp theo:
        1. Chuyển số đang CALLING → SERVING (nếu có).
        2. Lấy số WAITING nhỏ nhất → CALLING.
        """
        today = issue_date or date.today()

        # Chuyển CALLING → SERVING
        current = await self.get_current_calling(db, issue_date=today)
        if current:
            current.status = QueueStatus.SERVING
            current.served_at = datetime.now(timezone.utc)
            db.add(current)

        # Lấy số chờ tiếp theo
        result = await db.execute(
            select(QueueTicket)
            .where(
                and_(
                    QueueTicket.issue_date == today,
                    QueueTicket.status == QueueStatus.WAITING,
                )
            )
            .order_by(QueueTicket.sequence)
            .limit(1)
        )
        next_ticket = result.scalar_one_or_none()
        if next_ticket:
            next_ticket.status = QueueStatus.CALLING
            next_ticket.called_at = datetime.now(timezone.utc)
            db.add(next_ticket)
            await db.flush()
            await db.refresh(next_ticket)
        return next_ticket

    async def update_status(
        self,
        db: AsyncSession,
        *,
        ticket: QueueTicket,
        obj_in: QueueTicketStatusUpdate,
    ) -> QueueTicket:
        """Cập nhật trạng thái thủ công với timestamp tương ứng."""
        now = datetime.now(timezone.utc)

        ticket.status = obj_in.status
        if obj_in.counter_number is not None:
            ticket.counter_number = obj_in.counter_number
        if obj_in.note is not None:
            ticket.note = obj_in.note

        if obj_in.status == QueueStatus.CALLING:
            ticket.called_at = now
        elif obj_in.status == QueueStatus.SERVING:
            ticket.served_at = now
        elif obj_in.status in (QueueStatus.DONE, QueueStatus.SKIPPED):
            ticket.done_at = now

        db.add(ticket)
        await db.flush()
        await db.refresh(ticket)
        return ticket

    async def skip_ticket(
        self, db: AsyncSession, *, ticket: QueueTicket
    ) -> QueueTicket:
        """Đánh dấu bỏ qua (không có mặt)."""
        ticket.status = QueueStatus.SKIPPED
        ticket.done_at = datetime.now(timezone.utc)
        db.add(ticket)
        await db.flush()
        await db.refresh(ticket)
        return ticket

    async def complete_ticket(
        self, db: AsyncSession, *, ticket: QueueTicket
    ) -> QueueTicket:
        """Hoàn thành số thứ tự."""
        ticket.status = QueueStatus.DONE
        ticket.done_at = datetime.now(timezone.utc)
        db.add(ticket)
        await db.flush()
        await db.refresh(ticket)
        return ticket


crud_queue_ticket = CRUDQueueTicket(QueueTicket)
