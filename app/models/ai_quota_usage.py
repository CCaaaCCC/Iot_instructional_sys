"""AI 每日配额计数模型。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AiQuotaUsage(Base):
    """AI 每日配额计数（独立于会话，删除会话不影响配额）。

    设计要点：
    - (user_id, date) 联合唯一：每用户每天一行
    - count 累加每次成功调用（chat+reasoner 合计）
    - 删除会话不会重置配额，避免被绕过
    - 跨日自动新建行（无需显式重置）
    """

    __tablename__ = "ai_quota_usage"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_call_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
