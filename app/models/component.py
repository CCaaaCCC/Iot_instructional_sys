from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ComponentStatus, ComponentType, SensorMetric


class Component(Base):
    __tablename__ = "components"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("device_nodes.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[ComponentType] = mapped_column(Enum(ComponentType), nullable=False)
    status: Mapped[ComponentStatus] = mapped_column(
        Enum(ComponentStatus), default=ComponentStatus.off
    )
    metric: Mapped[SensorMetric | None] = mapped_column(Enum(SensorMetric), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    node = relationship("DeviceNode", back_populates="components")
