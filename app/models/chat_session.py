"""AI 对话会话模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ChatSession(Base):
    """AI 对话会话。一个用户可有多个会话，支持历史回看。

    设计要点：
    - user_id 隔离：用户只能访问自己的会话（隐私优先，教师无法查看学生对话）
    - role_hint 快照创建时的用户角色，便于审计
    - title 在首条消息后自动生成（截断 AI_SESSION_TITLE_MAXLEN 字符）
    - messages 级联删除（删除会话时一并删除消息）
    """

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    # 创建会话时的用户角色快照，便于审计（不随用户角色变化）
    role_hint: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
