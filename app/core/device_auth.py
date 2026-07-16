"""设备鉴权依赖：用于 ESP32/CAM/S3 设备调用 API 时的身份校验。

设计要点：
- 与用户 JWT 鉴权（core/dependencies.py）独立，但共用 Bearer 头
- 设备调用 API 时携带 `Authorization: Bearer <device_token>`
- DeviceContext 是设备身份上下文，包含 group_id/node_id/device_type，业务层据此做数据隔离
- 每个设备路由显式声明 `Depends(get_device_context)`，与 `require_roles` 二选一
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models import DeviceToken
from app.services import device_token_service

# 设备 token 使用独立的 HTTPBearer 实例（与 oauth2_scheme 区分）
# auto_error=False 以便自定义 401 响应信息
_device_bearer = HTTPBearer(
    scheme_name="deviceToken",
    auto_error=False,
    description="Device token issued via /device-tokens endpoint",
)


@dataclass
class DeviceContext:
    """设备鉴权上下文：业务层通过此对象获取 group_id 进行数据隔离。"""

    token: DeviceToken
    group_id: int
    node_id: int
    device_type: str


def get_device_context(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_device_bearer),
) -> DeviceContext:
    """设备鉴权依赖：校验 Bearer token 并返回 DeviceContext。

    Raises:
        HTTPException 401: 缺少凭证 / 凭证格式错误 / token 无效或已吊销。
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid device token. Use: Authorization: Bearer <device_token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_str = credentials.credentials
    token = device_token_service.verify_token(db, token_str)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked device token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return DeviceContext(
        token=token,
        group_id=token.group_id,
        node_id=token.node_id,
        device_type=token.device_type.value,
    )
