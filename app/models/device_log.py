from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ComponentStatus


class DeviceOperationLog(Base):
    __tablename__ = "device_operation_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int | None] = mapped_column(ForeignKey("device_nodes.id"), nullable=True)
    component_id: Mapped[int | None] = mapped_column(ForeignKey("components.id"), nullable=True)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[ComponentStatus] = mapped_column(Enum(ComponentStatus), nullable=False)
    message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    node = relationship("DeviceNode")
    component = relationship("Component")
    operator = relationship("User")
