from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DeviceType


class DeviceTokenCreate(BaseModel):
    """创建设备令牌请求：教师/管理员为指定小组的某类设备签发 token。"""

    group_id: int = Field(..., description="所属小组 ID")
    device_type: DeviceType = Field(..., description="设备类型: esp32/esp32cam/esp32s3/esp32s3_monitor")
    device_name: str = Field(..., min_length=1, max_length=50, description="设备名称")
    node_id: int = Field(..., description="关联的设备节点 ID")


class DeviceTokenOut(BaseModel):
    """设备令牌列表/详情响应（不含明文 token，重置/创建时才返回）。"""

    id: int
    group_id: int
    device_type: DeviceType
    device_name: str
    node_id: int
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DeviceTokenWithSecret(DeviceTokenOut):
    """创建/重置后返回，包含明文 token（仅此一次展示）。"""

    token: str


class DeviceTokenListOut(DeviceTokenOut):
    """列表项：附带小组/节点名称，便于管理端展示。"""

    group_name: str | None = None
    node_name: str | None = None
