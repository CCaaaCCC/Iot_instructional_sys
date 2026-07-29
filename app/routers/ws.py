import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.security import decode_access_token
from app.core.websocket_manager import ws_manager
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)) -> None:
    """WebSocket 实时数据推送端点。

    认证通过查询参数中的 JWT token。
    - 教师/管理员：接收所有节点的数据
    - 学生：只接收自己小组所属节点的数据
    """
    # 验证 JWT
    try:
        payload = decode_access_token(token)
        if payload is None or "sub" not in payload:
            await websocket.close(code=4001, reason="Invalid token")
            return
        user_id = int(payload["sub"])
    except (ValueError, Exception):
        await websocket.close(code=4001, reason="Invalid token")
        return

    # 查找用户
    from app.services import user_service
    db = SessionLocal()
    try:
        user = user_service.get_user_by_id(db, user_id)
        if not user or not user.is_active:
            await websocket.close(code=4003, reason="User not found or inactive")
            return

        # 确定 node_id 范围
        role = user.role.value
        node_id: int | None = None
        if role == "student" and user.group_id is not None:
            from app.services import group_service
            group = group_service.get_group(db, user.group_id)
            if group and group.node_id is not None:
                node_id = group.node_id
            else:
                node_id = 0  # 学生未绑定到节点，不会收到任何传感器数据
        # 教师/管理员: node_id=None → 广播所有数据

        await ws_manager.connect(websocket, user_id=user_id, role=role, node_id=node_id)

        # 接收循环
        while True:
            try:
                msg = await websocket.receive_text()
                if msg == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break
            except Exception:
                logger.exception("WS receive error for user=%s", user_id)
                break
    finally:
        db.close()
        await ws_manager.disconnect(websocket)
