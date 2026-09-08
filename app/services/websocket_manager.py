"""
WebSocket Connection Manager — quản lý kết nối và broadcast real-time.

Phân nhóm client theo "room" để gửi message đúng đối tượng:
- ``"display"``   : Màn hình LED hiển thị số đang gọi (công khai).
- ``"kiosk"``     : Kiosk / quầy lấy số thứ tự của bệnh nhân.
- ``"reception"`` : Giao diện quầy tiếp đón dành cho nhân viên.

Singleton ``ws_manager`` được import và dùng trực tiếp bởi các endpoint.
"""
import json
import logging
from typing import Dict, List, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Quản lý danh sách WebSocket connections và broadcast message theo room.

    Duy trì một dict nội bộ ``_connections`` phân nhóm connections theo tên room.
    Khi broadcast, các connections đã ngắt kết nối sẽ được dọn dẹp tự động.

    Attributes:
        _connections: Dict ánh xạ ``room_name → list[WebSocket]``.
            Được khởi tạo với ba room mặc định: ``display``, ``kiosk``, ``reception``.
    """

    def __init__(self):
        """Khởi tạo manager với ba room mặc định."""
        # Phân nhóm connections theo "room": "display", "kiosk", "reception"
        self._connections: Dict[str, List[WebSocket]] = {
            "display":   [],
            "kiosk":     [],
            "reception": [],
        }

    async def connect(self, websocket: WebSocket, room: str = "display") -> None:
        """
        Chấp nhận kết nối WebSocket mới và đăng ký vào room tương ứng.

        Gọi ``websocket.accept()`` trước, sau đó thêm vào danh sách của room.
        Nếu room chưa tồn tại, tự động tạo mới.

        Args:
            websocket: WebSocket connection cần đăng ký.
            room: Tên room cần tham gia (mặc định ``"display"``).
        """
        await websocket.accept()
        if room not in self._connections:
            self._connections[room] = []
        self._connections[room].append(websocket)
        logger.info(f"WebSocket connected: room={room}, total={len(self._connections[room])}")

    def disconnect(self, websocket: WebSocket, room: str = "display") -> None:
        """
        Xoá WebSocket khỏi room khi client ngắt kết nối.

        Bỏ qua nếu websocket không tồn tại trong danh sách
        (trường hợp đã bị dọn dẹp trước đó khi broadcast lỗi).

        Args:
            websocket: WebSocket connection cần xoá.
            room: Tên room cần xoá khỏi (mặc định ``"display"``).
        """
        if room in self._connections:
            try:
                self._connections[room].remove(websocket)
            except ValueError:
                pass
        logger.info(f"WebSocket disconnected: room={room}")

    async def broadcast(self, room: str, data: Any) -> None:
        """
        Gửi message tới tất cả clients đang kết nối trong một room.

        Serialize ``data`` thành JSON (``ensure_ascii=False`` để giữ tiếng Việt).
        Các connections bị lỗi khi gửi sẽ được dọn dẹp sau khi vòng lặp kết thúc.

        Args:
            room: Tên room cần broadcast.
            data: Dữ liệu cần gửi — bất kỳ object serializable thành JSON.
                  Các kiểu không serialize được (VD: ``date``) được xử lý bởi
                  ``default=str``.
        """
        if room not in self._connections:
            return
        payload = json.dumps(data, ensure_ascii=False, default=str)
        dead: List[WebSocket] = []
        for ws in list(self._connections[room]):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        # Dọn dẹp kết nối đã chết
        for ws in dead:
            self.disconnect(ws, room)

    async def broadcast_all(self, data: Any) -> None:
        """
        Broadcast message tới tất cả clients ở mọi room.

        Tiện ích khi cần thông báo toàn hệ thống (VD: bảo trì, reload).

        Args:
            data: Dữ liệu cần gửi tới tất cả rooms.
        """
        for room in self._connections:
            await self.broadcast(room, data)

    async def broadcast_queue_update(self, queue_data: dict) -> None:
        """
        Shortcut broadcast cập nhật hàng đợi tới màn hình LED và quầy tiếp đón.

        Gửi tới room ``"display"`` và ``"reception"`` với type ``"queue_update"``.
        Kiosk không nhận loại message này vì không cần hiển thị tổng hợp hàng đợi.

        Args:
            queue_data: Dict thống kê hàng đợi — thường là kết quả của
                :meth:`~app.crud.queue_ticket.CRUDQueueTicket.get_summary`.
        """
        payload = {"type": "queue_update", "data": queue_data}
        await self.broadcast("display",   payload)
        await self.broadcast("reception", payload)

    async def broadcast_new_ticket(self, ticket_data: dict) -> None:
        """
        Thông báo số thứ tự mới vừa được cấp tới kiosk và quầy tiếp đón.

        Gửi tới room ``"kiosk"`` và ``"reception"`` với type ``"new_ticket"``.
        Màn hình LED không cần nhận vì chỉ hiển thị số đang được gọi.

        Args:
            ticket_data: Dict thông tin số thứ tự mới (id, ticket_number, sequence…).
        """
        payload = {"type": "new_ticket", "data": ticket_data}
        await self.broadcast("kiosk",     payload)
        await self.broadcast("reception", payload)

    async def broadcast_calling(
        self,
        ticket_number: str,
        counter_number: int | None,
        patient_name: str | None,
    ) -> None:
        """
        Phát thông báo gọi số mới tới tất cả rooms (màn hình LED, kiosk, quầy).

        Gửi tới cả ba room với type ``"calling"``. Màn hình LED dùng để hiển thị
        số to; kiosk và quầy tiếp đón dùng để highlight số đang gọi.

        Args:
            ticket_number: Số thứ tự đang được gọi (VD: ``"A001"``).
            counter_number: Số quầy bệnh nhân cần đến (có thể ``None``).
            patient_name: Tên bệnh nhân nếu đã đăng ký (có thể ``None``).
        """
        payload = {
            "type": "calling",
            "data": {
                "ticket_number":  ticket_number,
                "counter_number": counter_number,
                "patient_name":   patient_name,
            },
        }
        await self.broadcast("display",   payload)
        await self.broadcast("kiosk",     payload)
        await self.broadcast("reception", payload)


# Singleton instance — import và dùng trực tiếp trong các endpoint
ws_manager = ConnectionManager()
