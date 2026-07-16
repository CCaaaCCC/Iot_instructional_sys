"""设备令牌服务：负责签发、校验、重置、吊销设备 token。

设计要点：
- token 使用 `secrets.token_urlsafe(32)` 生成（43 字符 URL-safe base64），存为 String(64)
- 同一 (group_id, device_type) 组合唯一，避免同一组同类设备签发多个 token
- verify_token 会更新 last_used_at，便于管理端识别活跃设备
- 不提供明文 token 二次查询接口（创建/重置时一次性返回）
"""

import secrets
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DeviceNode, DeviceToken, Group
from app.models.enums import DeviceType
from app.schemas.device_token import DeviceTokenCreate


def _generate_token() -> str:
    """生成 URL-safe 64 字符以内的随机 token。"""
    return secrets.token_urlsafe(32)


def list_tokens(
    db: Session,
    group_id: int | None = None,
    device_type: DeviceType | None = None,
    is_active: bool | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[DeviceToken]:
    """列出设备令牌，支持按小组/类型/状态过滤。"""
    stmt = select(DeviceToken).order_by(DeviceToken.created_at.desc())
    if group_id is not None:
        stmt = stmt.where(DeviceToken.group_id == group_id)
    if device_type is not None:
        stmt = stmt.where(DeviceToken.device_type == device_type)
    if is_active is not None:
        stmt = stmt.where(DeviceToken.is_active.is_(is_active))
    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_token(db: Session, token_id: int) -> DeviceToken | None:
    return db.get(DeviceToken, token_id)


def create_token(db: Session, payload: DeviceTokenCreate) -> DeviceToken:
    """为指定小组的某类设备签发新 token。

    Raises:
        ValueError: 小组/节点不存在，或该组已有同类型设备令牌。
    """
    # 校验小组存在
    group = db.get(Group, payload.group_id)
    if not group:
        raise ValueError(f"Group {payload.group_id} not found")
    # 校验节点存在
    node = db.get(DeviceNode, payload.node_id)
    if not node:
        raise ValueError(f"DeviceNode {payload.node_id} not found")
    # 校验同组同类型未重复
    existing = db.execute(
        select(DeviceToken).where(
            DeviceToken.group_id == payload.group_id,
            DeviceToken.device_type == payload.device_type,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError(
            f"Group {payload.group_id} already has a {payload.device_type.value} device token "
            f"(id={existing.id}). Revoke or reset it instead."
        )

    token = DeviceToken(
        token=_generate_token(),
        group_id=payload.group_id,
        device_type=payload.device_type,
        device_name=payload.device_name,
        node_id=payload.node_id,
        is_active=True,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def reset_token(db: Session, token_id: int) -> DeviceToken:
    """重置 token 字符串（保持其他字段不变）。

    Raises:
        ValueError: 令牌不存在。
    """
    token = db.get(DeviceToken, token_id)
    if not token:
        raise ValueError(f"DeviceToken {token_id} not found")
    token.token = _generate_token()
    token.is_active = True  # 重置后自动激活
    token.updated_at = datetime.now()
    db.commit()
    db.refresh(token)
    return token


def revoke_token(db: Session, token_id: int) -> DeviceToken:
    """吊销令牌（设为 inactive，保留记录便于审计）。

    Raises:
        ValueError: 令牌不存在。
    """
    token = db.get(DeviceToken, token_id)
    if not token:
        raise ValueError(f"DeviceToken {token_id} not found")
    token.is_active = False
    token.updated_at = datetime.now()
    db.commit()
    db.refresh(token)
    return token


def delete_token(db: Session, token_id: int) -> None:
    """硬删除令牌记录（一般用 revoke 替代，仅清理时使用）。

    Raises:
        ValueError: 令牌不存在。
    """
    token = db.get(DeviceToken, token_id)
    if not token:
        raise ValueError(f"DeviceToken {token_id} not found")
    db.delete(token)
    db.commit()


def verify_token(db: Session, token_str: str) -> DeviceToken | None:
    """校验设备 token 字符串，返回令牌记录并更新 last_used_at。

    用于设备鉴权依赖：返回 None 表示无效/已吊销。
    """
    token = db.execute(
        select(DeviceToken).where(DeviceToken.token == token_str)
    ).scalar_one_or_none()
    if not token or not token.is_active:
        return None
    token.last_used_at = datetime.now()
    db.commit()
    db.refresh(token)
    return token
