"""AI 对话消息模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ChatMessage(Base):
    """AI 对话单条消息（user/assistant/system）。

    设计要点：
    - role: user=用户消息，assistant=AI回复，system=系统提示（一般不持久化，仅临时构建）
    - model_used: 仅 assistant 消息记录使用的模型（deepseek-chat/reasoner）
    - tokens_used: 可选，来自 API 响应的 usage 字段
    - 按 created_at 排序构建对话上下文
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user/assistant/system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    session = relationship("ChatSession", back_populates="messages")
