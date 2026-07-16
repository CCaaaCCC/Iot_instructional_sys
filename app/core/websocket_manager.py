import asyncio
import logging
from dataclasses import dataclass

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class WSConnection:
    websocket: WebSocket
    user_id: int
    role: str
    node_id: int | None  # None = teacher/admin (can see all), int = student (scoped)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, list[WSConnection]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, ws: WebSocket, user_id: int, role: str, node_id: int | None) -> None:
        await ws.accept()
        conn = WSConnection(websocket=ws, user_id=user_id, role=role, node_id=node_id)
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(conn)
        logger.info("WS connected: user=%s role=%s node_id=%s", user_id, role, node_id)

    async def disconnect(self, ws: WebSocket) -> None:
        for uid, conns in list(self._connections.items()):
            self._connections[uid] = [c for c in conns if c.websocket is not ws]
            if not self._connections[uid]:
                del self._connections[uid]
        logger.info("WS disconnected: total_users=%s", len(self._connections))

    async def broadcast(self, event_type: str, data: dict, node_id: int | None = None) -> None:
        """广播事件。node_id=None 表示发给所有人，否则按 node_id 过滤。"""
        dead: list[tuple[int, WSConnection]] = []
        for uid, conns in list(self._connections.items()):
            for conn in conns:
                # 学生只看自己组的数据
                if conn.node_id is not None and node_id is not None and conn.node_id != node_id:
                    continue
                try:
                    await conn.websocket.send_json({"type": event_type, "data": data})
                except Exception:
                    dead.append((uid, conn))
        for uid, conn in dead:
            if uid in self._connections and conn in self._connections[uid]:
                self._connections[uid].remove(conn)
                if not self._connections[uid]:
                    del self._connections[uid]

    def broadcast_sync(self, event_type: str, data: dict, node_id: int | None = None) -> None:
        """同步版本的广播（在非 asyncio 线程中使用，如 paho-mqtt 回调）。"""
        if self._loop is None:
            logger.warning("No event loop set, cannot broadcast %s", event_type)
            return
        # 安全边界：降级为仅记录无法投递的情况（非紧急）
        try:
            asyncio.run_coroutine_threadsafe(
                self.broadcast(event_type, data, node_id), self._loop
            )
        except Exception:
            logger.exception("Failed to schedule WS broadcast for %s", event_type)

    async def send_to_user(self, event_type: str, data: dict, user_id: int) -> None:
        """精确推送给指定用户的所有 WebSocket 连接。"""
        dead: list[WSConnection] = []
        conns = self._connections.get(user_id, [])
        for conn in conns:
            try:
                await conn.websocket.send_json({"type": event_type, "data": data})
            except Exception:
                dead.append(conn)
        for conn in dead:
            if user_id in self._connections and conn in self._connections[user_id]:
                self._connections[user_id].remove(conn)
                if not self._connections[user_id]:
                    del self._connections[user_id]

    def send_to_user_sync(self, event_type: str, data: dict, user_id: int) -> None:
        """同步版本：精确推送给指定用户（用于 service 层在同步上下文中触发通知）。"""
        if self._loop is None:
            logger.warning("No event loop set, cannot send %s to user %s", event_type, user_id)
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self.send_to_user(event_type, data, user_id), self._loop
            )
        except Exception:
            logger.exception("Failed to schedule WS send_to_user for %s", event_type)


ws_manager = ConnectionManager()
