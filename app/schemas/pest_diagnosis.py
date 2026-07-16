from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import DiagnosisResult


class PestDiagnosisOut(BaseModel):
    """诊断记录响应。"""

    id: int
    group_id: int
    node_id: int
    device_token_id: int
    image_url: str
    diagnosis_result: DiagnosisResult
    confidence: float
    suggestion: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PestDiagnosisListOut(PestDiagnosisOut):
    """列表项：附带小组/节点名称。"""

    group_name: str | None = None
    node_name: str | None = None


class PestDiagnosisUploadResponse(BaseModel):
    """设备上传后返回的诊断结果。"""

    id: int
    diagnosis_result: DiagnosisResult
    confidence: float
    suggestion: str | None
    image_url: str
    created_at: datetime
