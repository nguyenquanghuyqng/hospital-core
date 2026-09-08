"""
CRUD operations cho model :class:`~app.models.queue_ticket.QueueTicket`.

Quản lý toàn bộ vòng đời số thứ tự: tạo mới, truy vấn theo ngày/trạng thái,
gọi số tiếp theo, và các thao tác cập nhật trạng thái.
"""
from datetime import date, datetime, timezone
from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.queue_ticket import QueueTicket, QueueStatus
from app.schemas.queue_ticket import QueueTicketCreate, QueueTicketStatusUpdate


class CRUDQueueTicket(CRUDBase[QueueTicket]):
    """
    CRUD class cho QueueTicket — kế thừa :class:`~app.crud.base.CRUDBase`.

    Bổ sung logic nghiệp vụ: tạo số thứ tự với sequence tự tăng theo ngày,
    lấy hàng đợi hiện tại, gọi số tiếp theo với cơ chế transition trạng thái
    nguyên tử, và các thao tác bỏ qua / hoàn thành.
    """

    # ── Tạo mới ─────────────────────────────────────────────────────────────

    async def create_ticket(
        self,
        db: AsyncSession,
        *,
        obj_in: QueueTicketCreate,
        issue_date: Optional[date] = None,
        prefix: str = "A",
    ) -> QueueTicket:
        """
        Tạo số thứ tự mới cho ngày chỉ định (mặc định hôm nay).

        Sequence tự tăng theo ngày: mỗi ngày bắt đầu lại từ 1.
        ``ticket_number`` được định dạng là ``prefix + sequence`` 3 chữ số
        (VD: ``A001``, ``A002``…).

        Args:
            db: Async database session.
            obj_in: Schema :class:`~app.schemas.queue_ticket.QueueTicketCreate`.
            issue_date: Ngày cấp số (mặc định ``date.today()``).
            prefix: Ký tự đầu của ticket_number (mặc định ``"A"``).

        Returns:
            :class:`~app.models.queue_ticket.QueueTicket` vừa tạo với
            ``status=WAITING``.
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

    # ── Truy vấn ─────────────────────────────────────────────────────────────

    async def get_by_date(
        self,
        db: AsyncSession,
        *,
        issue_date: date,
        status: Optional[QueueStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[QueueTicket]:
        """
        Lấy danh sách số thứ tự theo ngày, tuỳ chọn lọc theo trạng thái.

        Args:
            db: Async database session.
            issue_date: Ngày cần truy vấn.
            status: Lọc theo trạng thái cụ thể (tuỳ chọn).
            skip: Offset phân trang.
            limit: Số bản ghi tối đa.

        Returns:
            Danh sách :class:`~app.models.queue_ticket.QueueTicket`
            sắp xếp theo ``sequence`` tăng dần.
        """
        query = select(QueueTicket).where(QueueTicket.issue_date == issue_date)
        if status:
            query = query.where(QueueTicket.status == status)
        query = query.order_by(QueueTicket.sequence).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_waiting_list(
        self, db: AsyncSession, *, issue_date: Optional[date] = None
    ) -> List[QueueTicket]:
        """
        Lấy danh sách số thứ tự đang chờ (WAITING) trong ngày.

        Args:
            db: Async database session.
            issue_date: Ngày cần xem (mặc định hôm nay).

        Returns:
            Danh sách :class:`~app.models.queue_ticket.QueueTicket` có
            ``status=WAITING``, sắp xếp theo ``sequence`` tăng dần.
        """
        today = issue_date or date.today()
        return await self.get_by_date(db, issue_date=today, status=QueueStatus.WAITING, limit=200)

    async def get_current_calling(
        self, db: AsyncSession, *, issue_date: Optional[date] = None
    ) -> Optional[QueueTicket]:
        """
        Lấy số thứ tự đang được gọi (CALLING) mới nhất trong ngày.

        Args:
            db: Async database session.
            issue_date: Ngày cần xem (mặc định hôm nay).

        Returns:
            :class:`~app.models.queue_ticket.QueueTicket` đang ở trạng thái
            CALLING (được gọi gần nhất), hoặc ``None`` nếu không có.
        """
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
        """
        Tổng hợp số lượng theo từng trạng thái trong ngày.

        Dùng cho dashboard real-time và broadcast WebSocket.

        Args:
            db: Async database session.
            issue_date: Ngày cần thống kê (mặc định hôm nay).

        Returns:
            Dict chứa: ``issue_date``, ``total``, ``waiting``, ``calling``,
            ``serving``, ``done``, ``skipped``, ``current_calling``
            (ticket_number đang được gọi hoặc ``None``).
        """
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
            "issue_date":       today,
            "total":            total,
            "waiting":          counts.get(QueueStatus.WAITING, 0),
            "calling":          counts.get(QueueStatus.CALLING, 0),
            "serving":          counts.get(QueueStatus.SERVING, 0),
            "done":             counts.get(QueueStatus.DONE, 0),
            "skipped":          counts.get(QueueStatus.SKIPPED, 0),
            "current_calling":  current.ticket_number if current else None,
        }

    # ── Cập nhật trạng thái ──────────────────────────────────────────────────

    async def call_next(
        self, db: AsyncSession, *, issue_date: Optional[date] = None
    ) -> Optional[QueueTicket]:
        """
        Gọi số thứ tự tiếp theo trong hàng đợi.

        Thực hiện hai bước nguyên tử trong cùng một flush:
        1. Chuyển số đang ``CALLING`` → ``SERVING`` (ghi ``served_at``).
        2. Lấy số ``WAITING`` nhỏ nhất → ``CALLING`` (ghi ``called_at``).

        Args:
            db: Async database session.
            issue_date: Ngày cần gọi số (mặc định hôm nay).

        Returns:
            :class:`~app.models.queue_ticket.QueueTicket` vừa được chuyển sang
            CALLING, hoặc ``None`` nếu hàng đợi trống.
        """
        today = issue_date or date.today()

        # Chuyển CALLING → SERVING
        current = await self.get_current_calling(db, issue_date=today)
        if current:
            current.status   = QueueStatus.SERVING
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
            next_ticket.status    = QueueStatus.CALLING
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
        """
        Cập nhật trạng thái số thứ tự thủ công với timestamp tương ứng.

        Tự động ghi timestamp phù hợp theo trạng thái mới:
        - CALLING  → ``called_at``
        - SERVING  → ``served_at``
        - DONE / SKIPPED → ``done_at``

        Args:
            db: Async database session.
            ticket: Instance :class:`~app.models.queue_ticket.QueueTicket` cần cập nhật.
            obj_in: Schema :class:`~app.schemas.queue_ticket.QueueTicketStatusUpdate`.

        Returns:
            :class:`~app.models.queue_ticket.QueueTicket` đã cập nhật.
        """
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
        """
        Đánh dấu số thứ tự là đã bỏ qua (SKIPPED) — gọi không có mặt.

        Args:
            db: Async database session.
            ticket: Instance :class:`~app.models.queue_ticket.QueueTicket` cần bỏ qua.

        Returns:
            :class:`~app.models.queue_ticket.QueueTicket` với
            ``status=SKIPPED`` và ``done_at`` đã được ghi.
        """
        ticket.status  = QueueStatus.SKIPPED
        ticket.done_at = datetime.now(timezone.utc)
        db.add(ticket)
        await db.flush()
        await db.refresh(ticket)
        return ticket

    async def complete_ticket(
        self, db: AsyncSession, *, ticket: QueueTicket
    ) -> QueueTicket:
        """
        Đánh dấu số thứ tự là đã hoàn thành (DONE).

        Args:
            db: Async database session.
            ticket: Instance :class:`~app.models.queue_ticket.QueueTicket` cần hoàn thành.

        Returns:
            :class:`~app.models.queue_ticket.QueueTicket` với
            ``status=DONE`` và ``done_at`` đã được ghi.
        """
        ticket.status  = QueueStatus.DONE
        ticket.done_at = datetime.now(timezone.utc)
        db.add(ticket)
        await db.flush()
        await db.refresh(ticket)
        return ticket


crud_queue_ticket = CRUDQueueTicket(QueueTicket)
"""Singleton instance của :class:`CRUDQueueTicket` dùng toàn ứng dụng."""
