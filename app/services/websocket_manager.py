"""
WebSocket Connection Manager — broadcast real-time queue updates
tới tất cả clients đang kết nối (màn hình LED, kiosk, quầy tiếp đón).
"""
import json
import logging
from typing import Dict, List, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Phân nhóm connections theo "room": "display", "kiosk", "reception"
        self._connections: Dict[str, List[WebSocket]] = {
            "display": [],
            "kiosk": [],
            "reception": [],
        }

    async def connect(self, websocket: WebSocket, room: str = "display") -> None:
        await websocket.accept()
        if room not in self._connections:
            self._connections[room] = []
        self._connections[room].append(websocket)
        logger.info(f"WebSocket connected: room={room}, total={len(self._connections[room])}")

    def disconnect(self, websocket: WebSocket, room: str = "display") -> None:
        if room in self._connections:
            try:
                self._connections[room].remove(websocket)
            except ValueError:
                pass
        logger.info(f"WebSocket disconnected: room={room}")

    async def broadcast(self, room: str, data: Any) -> None:
        """Gửi message tới tất cả clients trong room."""
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
        """Broadcast tới mọi room."""
        for room in self._connections:
            await self.broadcast(room, data)

    async def broadcast_queue_update(self, queue_data: dict) -> None:
        """
        Shortcut: gửi cập nhật hàng đợi.
        Tất cả màn hình LED và quầy tiếp đón nhận được.
        """
        payload = {"type": "queue_update", "data": queue_data}
        await self.broadcast("display", payload)
        await self.broadcast("reception", payload)

    async def broadcast_new_ticket(self, ticket_data: dict) -> None:
        """Thông báo có số thứ tự mới vừa được cấp."""
        payload = {"type": "new_ticket", "data": ticket_data}
        await self.broadcast("kiosk", payload)
        await self.broadcast("reception", payload)

    async def broadcast_calling(self, ticket_number: str, counter_number: int | None, patient_name: str | None) -> None:
        """Phát lên màn hình LED khi gọi số mới."""
        payload = {
            "type": "calling",
            "data": {
                "ticket_number": ticket_number,
                "counter_number": counter_number,
                "patient_name": patient_name,
            },
        }
        await self.broadcast("display", payload)
        await self.broadcast("kiosk", payload)
        await self.broadcast("reception", payload)


# Singleton instance
ws_manager = ConnectionManager()
