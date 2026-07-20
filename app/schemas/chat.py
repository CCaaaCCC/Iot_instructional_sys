"""AI 对话相关 schema。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatContext(BaseModel):
    """前端显式传递的页面上下文。"""

    route_name: str = Field(..., description="当前路由名，如 tasks/sensors/student-tasks")
    page_data: dict[str, Any] = Field(
        default_factory=dict, description="页面关键数据，如当前任务ID/传感器最新值"
    )


class ChatRequest(BaseModel):
    """发送消息请求体。"""

    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    session_id: int | None = Field(None, description="会话ID，None=新建会话")
    context: ChatContext | None = Field(None, description="页面上下文")


class ChatSessionCreate(BaseModel):
    """创建会话请求体。"""

    title: str | None = Field(None, description="可选自定义标题，默认用首条消息截断")


class ChatSessionRename(BaseModel):
    """重命名会话请求体。"""

    title: str = Field(..., min_length=1, max_length=120, description="新标题")


class ChatSessionOut(BaseModel):
    """会话输出（含最近消息预览）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    role_hint: str
    created_at: datetime
    updated_at: datetime
    last_message_preview: str | None = None


class ChatSessionListOut(ChatSessionOut):
    """会话列表项（同 ChatSessionOut）。"""

    pass


class ChatMessageOut(BaseModel):
    """单条消息输出。"""

    # model_used 字段触发 Pydantic 保护命名空间警告，显式关闭
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    role: str
    content: str
    model_used: str | None
    created_at: datetime


class AiQuotaOut(BaseModel):
    """配额查询输出。"""

    used: int
    limit: int
    remaining: int
    date: str  # ISO 日期字符串
