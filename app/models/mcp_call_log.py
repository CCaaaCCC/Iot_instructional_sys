from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class McpCallLog(Base):
    """小智 AI MCP 工具调用日志。

    ESP32-S3 设备通过 MCP 协议调用后端工具时记录每次调用，
    仅记工具调用元信息（工具名、参数、结果、耗时），不记对话原文，
    便于教师端审计与大赛展示。30 天后自动清理。
    """

    __tablename__ = "mcp_call_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 数据隔离：调用归属小组（来自 device_token.group_id）
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False, index=True)
    # 调用设备令牌（审计追溯）
    device_token_id: Mapped[int] = mapped_column(
        ForeignKey("device_tokens.id"), nullable=False, index=True
    )
    # 工具名（如 get_latest_sensor_data / control_components_by_type）
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # 调用参数（JSON 字符串）
    arguments: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 调用结果（JSON 字符串，失败时可能为 None）
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 调用耗时（毫秒）
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 是否成功
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # 错误信息（失败时填写）
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    # 过期时间（created_at + 30 天），到期后被 cleanup_expired_mcp_logs 清理
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # 关系
    group = relationship("Group")
    device_token = relationship("DeviceToken")
