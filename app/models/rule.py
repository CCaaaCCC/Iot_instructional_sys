from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ComponentStatus, ComponentType, RuleOperator, SensorMetric


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    metric: Mapped[SensorMetric] = mapped_column(Enum(SensorMetric), nullable=False)
    operator: Mapped[RuleOperator] = mapped_column(Enum(RuleOperator), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    action_component_type: Mapped[ComponentType] = mapped_column(Enum(ComponentType), nullable=False)
    action: Mapped[ComponentStatus] = mapped_column(Enum(ComponentStatus), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
