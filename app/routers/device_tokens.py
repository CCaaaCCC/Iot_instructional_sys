"""设备令牌管理路由：教师/管理员签发、列表、重置、吊销设备 token。

权限：
- 创建/重置/吊销：admin + operator + teacher（教师为本班设备签发）
- 列表：admin + operator + teacher
- 学生无权访问
- /me：设备自身用 Bearer token 校验身份（非用户 JWT）
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.core.device_auth import DeviceContext, get_device_context
from app.models.enums import UserRole
from app.schemas.device_token import (
    DeviceTokenCreate,
    DeviceTokenListOut,
    DeviceTokenOut,
    DeviceTokenWithSecret,
)
from app.services import device_token_service, log_service

router = APIRouter(prefix="/device-tokens", tags=["device-tokens"])


@router.get("", response_model=list[DeviceTokenListOut])
def list_device_tokens(
    group_id: int | None = None,
    device_type: str | None = None,
    is_active: bool | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(UserRole.admin, UserRole.operator, UserRole.teacher)
    ),
) -> list[DeviceTokenListOut]:
    """列出设备令牌，支持按小组/类型/状态过滤。"""
    # device_type 字符串转枚举（若提供）
    from app.models.enums import DeviceType

    type_enum = None
    if device_type:
        try:
            type_enum = DeviceType(device_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid device_type. Valid: {[t.value for t in DeviceType]}",
            )
    tokens = device_token_service.list_tokens(
        db,
        group_id=group_id,
        device_type=type_enum,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )
    result: list[DeviceTokenListOut] = []
    for t in tokens:
        group_name = t.group.name if t.group else None
        node_name = t.node.name if t.node else None
        result.append(
            DeviceTokenListOut(
                id=t.id,
                group_id=t.group_id,
                device_type=t.device_type,
                device_name=t.device_name,
                node_id=t.node_id,
                is_active=t.is_active,
                last_used_at=t.last_used_at,
                created_at=t.created_at,
                updated_at=t.updated_at,
                group_name=group_name,
                node_name=node_name,
            )
        )
    return result


@router.get("/me", response_model=DeviceTokenOut)
def verify_device_self(
    device: DeviceContext = Depends(get_device_context),
) -> DeviceTokenOut:
    """设备自检端点：设备用 Bearer token 校验身份，返回自身令牌信息。

    用途：设备启动时调用此接口确认 token 有效，并获取 group_id/node_id 上下文。
    鉴权：使用设备 token（非用户 JWT）。
    """
    return device.token


@router.post(
    "",
    response_model=DeviceTokenWithSecret,
    status_code=status.HTTP_201_CREATED,
)
def create_device_token(
    payload: DeviceTokenCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(UserRole.admin, UserRole.operator, UserRole.teacher)
    ),
) -> DeviceTokenWithSecret:
    """为指定小组的某类设备签发新 token（明文 token 仅此一次返回）。"""
    try:
        token = device_token_service.create_token(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="create_device_token",
        entity_type="device_token",
        entity_id=str(token.id),
        detail=f"Issued {token.device_type.value} token for group {token.group_id}",
    )
    return DeviceTokenWithSecret(
        id=token.id,
        group_id=token.group_id,
        device_type=token.device_type,
        device_name=token.device_name,
        node_id=token.node_id,
        is_active=token.is_active,
        last_used_at=token.last_used_at,
        created_at=token.created_at,
        updated_at=token.updated_at,
        token=token.token,
    )


@router.post(
    "/{token_id}/reset",
    response_model=DeviceTokenWithSecret,
)
def reset_device_token(
    token_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(UserRole.admin, UserRole.operator, UserRole.teacher)
    ),
) -> DeviceTokenWithSecret:
    """重置 token 字符串（旧 token 立即失效，新 token 仅此一次返回）。"""
    try:
        token = device_token_service.reset_token(db, token_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="reset_device_token",
        entity_type="device_token",
        entity_id=str(token.id),
        detail=f"Reset token for {token.device_type.value} (group {token.group_id})",
    )
    return DeviceTokenWithSecret(
        id=token.id,
        group_id=token.group_id,
        device_type=token.device_type,
        device_name=token.device_name,
        node_id=token.node_id,
        is_active=token.is_active,
        last_used_at=token.last_used_at,
        created_at=token.created_at,
        updated_at=token.updated_at,
        token=token.token,
    )


@router.post(
    "/{token_id}/revoke",
    response_model=DeviceTokenOut,
)
def revoke_device_token(
    token_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(UserRole.admin, UserRole.operator, UserRole.teacher)
    ),
) -> DeviceTokenOut:
    """吊销令牌（设为 inactive，设备调用将返回 401）。"""
    try:
        token = device_token_service.revoke_token(db, token_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="revoke_device_token",
        entity_type="device_token",
        entity_id=str(token.id),
        detail=f"Revoked {token.device_type.value} token (group {token.group_id})",
    )
    return token


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device_token(
    token_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin)),
) -> None:
    """硬删除令牌记录（仅 admin，一般用 revoke 替代）。"""
    try:
        device_token_service.delete_token(db, token_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="delete_device_token",
        entity_type="device_token",
        entity_id=str(token_id),
        detail="Deleted device token record",
    )
