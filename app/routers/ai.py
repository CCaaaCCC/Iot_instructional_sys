"""AI 助手路由：会话管理 + 流式对话 + 配额查询。

权限：
- 所有端点仅 admin/teacher/student 可用（operator 无 AI 助手权限）
- 会话按 user_id 隔离：用户只能访问自己的会话
- chat 端点返回 SSE 流式响应
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.enums import UserRole
from app.schemas.chat import (
    AiQuotaOut,
    ChatMessageOut,
    ChatRequest,
    ChatSessionCreate,
    ChatSessionListOut,
    ChatSessionOut,
    ChatSessionRename,
)
from app.services import ai_service, log_service

router = APIRouter(prefix="/ai", tags=["ai"])

# AI 助手可用角色（operator 无权限）
_AI_ROLES = (UserRole.admin, UserRole.teacher, UserRole.student)


@router.post("/sessions", response_model=ChatSessionOut, status_code=201)
def create_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_AI_ROLES)),
) -> ChatSessionOut:
    """创建新会话。"""
    session = ai_service.create_session(db, current_user, title=payload.title)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="create_ai_session",
        entity_type="chat_session",
        entity_id=str(session.id),
        detail=f"Created AI chat session #{session.id}",
    )
    return ChatSessionOut.model_validate(
        {**session.__dict__, "last_message_preview": None}
    )


@router.get("/sessions", response_model=list[ChatSessionListOut])
def list_sessions(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_AI_ROLES)),
) -> list[ChatSessionListOut]:
    """列出当前用户的所有会话（按更新时间倒序）。"""
    sessions = ai_service.list_sessions(db, current_user, skip=skip, limit=limit)
    result: list[ChatSessionListOut] = []
    for s in sessions:
        preview = ai_service.get_last_message_preview(db, s.id)
        result.append(
            ChatSessionListOut.model_validate(
                {**s.__dict__, "last_message_preview": preview}
            )
        )
    return result


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
def get_messages(
    session_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_AI_ROLES)),
) -> list[ChatMessageOut]:
    """获取会话消息（按时间正序）。"""
    messages = ai_service.get_session_messages(db, session_id, current_user, limit=limit)
    return [ChatMessageOut.model_validate(m) for m in messages]


@router.patch("/sessions/{session_id}", response_model=ChatSessionOut)
def rename_session(
    session_id: int,
    payload: ChatSessionRename,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_AI_ROLES)),
) -> ChatSessionOut:
    """重命名会话。"""
    session = ai_service.rename_session(db, session_id, current_user, payload.title)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在或无权访问")
    return ChatSessionOut.model_validate(
        {**session.__dict__, "last_message_preview": ai_service.get_last_message_preview(db, session.id)}
    )


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_AI_ROLES)),
):
    """删除会话及其所有消息。"""
    ok = ai_service.delete_session(db, session_id, current_user)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在或无权访问")
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="delete_ai_session",
        entity_type="chat_session",
        entity_id=str(session_id),
        detail=f"Deleted AI chat session #{session_id}",
    )


@router.get("/quota", response_model=AiQuotaOut)
def get_quota(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_AI_ROLES)),
) -> AiQuotaOut:
    """查询今日 AI 调用配额。"""
    quota = ai_service.get_quota(db, current_user)
    return AiQuotaOut(**quota)


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_AI_ROLES)),
) -> StreamingResponse:
    """流式对话端点（SSE）。

    请求体：{message, session_id?, context?}
    - session_id 为 None 时自动创建新会话
    - context 为前端显式传递的页面上下文（route_name + page_data）

    SSE 事件格式：
    - data: {"type":"session","session_id":123}\n\n  （会话ID，首个事件）
    - data: {"type":"delta","content":"片段"}\n\n  （逐字输出）
    - data: {"type":"done","message_id":456,"model":"..."}\n\n  （完成）
    - data: {"type":"error","message":"..."}\n\n  （错误）
    """
    # 创建或获取会话
    is_new_session = payload.session_id is None
    if is_new_session:
        session = ai_service.create_session(db, current_user)
    else:
        session = ai_service.get_session(db, payload.session_id, current_user)
        if session is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在或无权访问")

    session_id = session.id

    async def event_stream():
        # 首个事件：发送会话ID（让前端知道当前会话）
        yield ai_service.sse_event("session", {"session_id": session_id})
        # 后续：流式生成（传 is_new_session 便于失败时清理空会话）
        async for event in ai_service.stream_chat(
            db, current_user, session, payload.message, payload.context,
            is_new_session=is_new_session,
        ):
            yield event
        # 保持连接短暂时间后再正常关闭，让客户端有机会读取到流末尾（done=true），
        # 避免浏览器将服务器关闭识别为 net::ERR_ABORTED。
        await asyncio.sleep(2.0)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx 关闭缓冲
        },
    )
