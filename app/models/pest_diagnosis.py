from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DiagnosisResult


class PestDiagnosis(Base):
    """ESP32-CAM 视觉节点的病虫害诊断记录。

    设备通过 device_token 鉴权上传照片，后端 mock AI 分类后返回结果，
    并通过 WebSocket 实时推送给同组学生 + 教师。
    """

    __tablename__ = "pest_diagnoses"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 数据隔离：诊断归属小组
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False, index=True)
    # 上报节点
    node_id: Mapped[int] = mapped_column(ForeignKey("device_nodes.id"), nullable=False, index=True)
    # 上报设备令牌（审计追溯）
    device_token_id: Mapped[int] = mapped_column(
        ForeignKey("device_tokens.id"), nullable=False, index=True
    )
    # 照片 URL（存储在 data/pest-images/ 下）
    image_url: Mapped[str] = mapped_column(String(255), nullable=False)
    # 诊断结果（6 分类枚举）
    diagnosis_result: Mapped[DiagnosisResult] = mapped_column(nullable=False, index=True)
    # 置信度 0-1
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # 处理建议
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    # 关系
    group = relationship("Group")
    node = relationship("DeviceNode")
    device_token = relationship("DeviceToken")
