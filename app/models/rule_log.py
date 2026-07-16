from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RuleLog(Base):
    __tablename__ = "rule_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("rules.id"), nullable=False)
    sensor_data_id: Mapped[int | None] = mapped_column(
        ForeignKey("sensor_data.id"), nullable=True
    )
    node_id: Mapped[int | None] = mapped_column(ForeignKey("device_nodes.id"), nullable=True)
    component_id: Mapped[int | None] = mapped_column(ForeignKey("components.id"), nullable=True)
    message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    rule = relationship("Rule")
    sensor_data = relationship("SensorData")
    node = relationship("DeviceNode")
    component = relationship("Component")
