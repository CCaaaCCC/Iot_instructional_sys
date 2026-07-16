from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DeviceType


class DeviceToken(Base):
    """设备鉴权令牌：每个小组的 3 个设备（ESP32/CAM/S3）各持独立 token，绑定到同一 group_id。"""

    __tablename__ = "device_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    # token 明文（64 字符，secrets.token_urlsafe(32) 生成），唯一索引
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    # 所属小组（数据隔离的核心：token → group_id → 只能访问本组数据）
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False, index=True)
    # 设备类型
    device_type: Mapped[DeviceType] = mapped_column(nullable=False)
    # 设备名称（便于管理端识别）
    device_name: Mapped[str] = mapped_column(String(50), nullable=False)
    # 关联的设备节点（ESP32 主节点；CAM/S3 可关联同一节点）
    node_id: Mapped[int] = mapped_column(ForeignKey("device_nodes.id"), nullable=False)
    # 是否激活
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # 最后使用时间
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # 关系
    group = relationship("Group")
    node = relationship("DeviceNode")
