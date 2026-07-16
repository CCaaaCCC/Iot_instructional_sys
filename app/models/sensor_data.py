from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SensorData(Base):
    __tablename__ = "sensor_data"
    __table_args__ = (
        Index("ix_sensor_data_node_recorded", "node_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("device_nodes.id"), nullable=False)
    air_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    air_humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    light_intensity: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_ph: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    node = relationship("DeviceNode")
