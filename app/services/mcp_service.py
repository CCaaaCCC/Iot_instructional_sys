"""MCP 服务层：小智 AI 工具集分发器。

设计要点：
- 所有工具自动 scope 到 device_context.group_id，**不接受外部传入 group_id**
- control_components_by_type 按类型批量控制本组执行器（语音场景友好）
- 每次调用写 McpCallLog（含 duration_ms + expires_at=now+30天），不记对话原文
- 6 个工具为最小集（读 + 控制），不含创建/规则管理/任务管理
"""

import json
import logging
import time
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.device_auth import DeviceContext
from app.models.class_task import ClassTask
from app.models.component import Component
from app.models.crop import Crop
from app.models.device_node import DeviceNode
from app.models.enums import ComponentStatus, ComponentType, TaskStatus
from app.models.group import Group
from app.models.mcp_call_log import McpCallLog
from app.models.rule import Rule
from app.models.sensor_data import SensorData
from app.services import device_node_service

logger = logging.getLogger(__name__)

LOG_RETENTION_DAYS = 30


# ---------------------------------------------------------------------------
# 工具定义
# ---------------------------------------------------------------------------

def list_tools() -> list[dict]:
    """返回 MCP 工具清单（JSON Schema 风格，供小智 AI 解析能力）。"""
    return [
        {
            "name": "get_latest_sensor_data",
            "description": "获取本组的最新环境数据（气温、湿度、土壤温湿度、光照、pH）",
            "parameters": {},
        },
        {
            "name": "control_components_by_type",
            "description": "按类型控制本组所有执行器（如'打开风扇'会控制本组所有风扇）。类型可选: fan/pump/light",
            "parameters": {
                "component_type": {
                    "type": "string",
                    "description": "执行器类型",
                    "enum": ["fan", "pump", "light"],
                },
                "action": {
                    "type": "string",
                    "description": "控制动作",
                    "enum": ["on", "off", "auto"],
                },
            },
        },
        {
            "name": "get_group_components",
            "description": "查询本组所有执行器（风扇/水泵/补光灯）的当前状态",
            "parameters": {},
        },
        {
            "name": "get_crop_status",
            "description": "查询本组的作物生长状态",
            "parameters": {},
        },
        {
            "name": "list_pending_tasks",
            "description": "列出本组的未完成课堂任务",
            "parameters": {
                "limit": {
                    "type": "integer",
                    "description": "返回条数上限，默认 5",
                    "default": 5,
                }
            },
        },
        {
            "name": "list_group_rules",
            "description": "查询本组节点启用的自动控制规则",
            "parameters": {
                "enabled_only": {
                    "type": "boolean",
                    "description": "是否仅返回启用的规则，默认 true",
                    "default": True,
                }
            },
        },
    ]


# ---------------------------------------------------------------------------
# 工具实现（全部基于 device_context.group_id 自动 scope）
# ---------------------------------------------------------------------------

def _tool_get_latest_sensor_data(db: Session, device: DeviceContext) -> dict:
    """工具1：获取本组最新传感器数据。"""
    group = db.get(Group, device.group_id)
    if not group or group.node_id is None:
        return {"found": False, "message": "本组未绑定设备节点"}

    stmt = (
        select(SensorData)
        .where(SensorData.node_id == group.node_id)
        .order_by(SensorData.recorded_at.desc())
        .limit(1)
    )
    row = db.execute(stmt).scalar_one_or_none()
    if not row:
        return {"found": False, "message": "本组暂无传感器数据"}

    return {
        "found": True,
        "node_id": row.node_id,
        "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
        "air_temp": row.air_temp,
        "air_humidity": row.air_humidity,
        "soil_temp": row.soil_temp,
        "soil_humidity": row.soil_humidity,
        "light_intensity": row.light_intensity,
        "soil_ph": row.soil_ph,
    }


def _tool_control_components_by_type(
    db: Session, device: DeviceContext, component_type: str, action: str
) -> dict:
    """工具2：按类型控制本组所有执行器。

    核心安全设计：通过 device.group_id → group.node_id 查询本组组件，
    从设计上杜绝跨组控制。
    """
    # 参数校验
    try:
        ctype = ComponentType(component_type)
    except ValueError:
        return {
            "controlled_count": 0,
            "error": f"Invalid component_type: {component_type}. Valid: fan/pump/light",
        }
    try:
        action_enum = ComponentStatus(action)
    except ValueError:
        return {
            "controlled_count": 0,
            "error": f"Invalid action: {action}. Valid: on/off/auto",
        }

    group = db.get(Group, device.group_id)
    if not group or group.node_id is None:
        return {"controlled_count": 0, "error": "本组未绑定设备节点"}

    # 查询本组节点下所有该类型组件（自动 scope，不接受外部 node_id）
    components = device_node_service.list_components(
        db, node_id=group.node_id, component_type=ctype
    )

    controlled: list[dict] = []
    for comp in components:
        device_node_service.control_component(
            db,
            component=comp,
            action=action_enum,
            operator_id=None,  # 设备操作，无用户 ID
            message=f"MCP tool control_components_by_type ({ctype.value}->{action_enum.value}) by device_token#{device.token.id}",
        )
        controlled.append(
            {"id": comp.id, "name": comp.name, "type": comp.type.value, "status": comp.status.value}
        )

    return {
        "controlled_count": len(controlled),
        "components": controlled,
        "component_type": ctype.value,
        "action": action_enum.value,
    }


def _tool_get_group_components(db: Session, device: DeviceContext) -> dict:
    """工具3：查询本组所有执行器状态。"""
    group = db.get(Group, device.group_id)
    if not group or group.node_id is None:
        return {"found": False, "message": "本组未绑定设备节点"}

    components = device_node_service.list_components(db, node_id=group.node_id)
    # 仅返回执行器（风扇/水泵/补光灯），过滤掉传感器
    actors = [
        {
            "id": c.id,
            "name": c.name,
            "type": c.type.value,
            "status": c.status.value,
        }
        for c in components
        if c.type != ComponentType.sensor
    ]
    return {
        "found": True,
        "node_id": group.node_id,
        "components": actors,
        "total": len(actors),
    }


def _tool_get_crop_status(db: Session, device: DeviceContext) -> dict:
    """工具4：查询本组作物信息。"""
    stmt = select(Crop).where(Crop.group_id == device.group_id)
    crops = db.execute(stmt).scalars().all()
    if not crops:
        return {"found": False, "message": "本组暂无作物记录"}

    return {
        "found": True,
        "crops": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "growth_stage": c.growth_stage,
                "start_date": c.start_date.isoformat() if c.start_date else None,
                "end_date": c.end_date.isoformat() if c.end_date else None,
                "notes": c.notes,
            }
            for c in crops
        ],
        "total": len(crops),
    }


def _tool_list_pending_tasks(
    db: Session, device: DeviceContext, limit: int = 5
) -> dict:
    """工具5：列出本组未完成任务。"""
    # 限制 limit 范围
    limit = max(1, min(int(limit), 20))
    stmt = (
        select(ClassTask)
        .where(
            ClassTask.group_id == device.group_id,
            ClassTask.status != TaskStatus.done,
        )
        .order_by(ClassTask.created_at.desc())
        .limit(limit)
    )
    tasks = db.execute(stmt).scalars().all()
    return {
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "status": t.status.value if t.status else None,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "task_type": t.task_type.value if t.task_type else None,
            }
            for t in tasks
        ],
        "total": len(tasks),
    }


def _tool_list_group_rules(
    db: Session, device: DeviceContext, enabled_only: bool = True
) -> dict:
    """工具6：获取本组节点的自动控制规则。

    注意：Rule 模型按 action_component_type 触发，作用于具体 node_id 的组件，
    因此这里返回所有规则（规则本身是节点级的，通过 component 查询时已 scope）。
    """
    group = db.get(Group, device.group_id)
    if not group or group.node_id is None:
        return {"found": False, "message": "本组未绑定设备节点"}

    stmt = select(Rule)
    if enabled_only:
        stmt = stmt.where(Rule.enabled.is_(True))
    stmt = stmt.order_by(Rule.created_at.desc())
    rules = db.execute(stmt).scalars().all()

    # 过滤：仅返回本组节点存在对应类型组件的规则（更精准的 scope）
    node_components = device_node_service.list_components(db, node_id=group.node_id)
    node_component_types = {c.type for c in node_components}
    scoped_rules = [r for r in rules if r.action_component_type in node_component_types]

    return {
        "found": True,
        "node_id": group.node_id,
        "rules": [
            {
                "id": r.id,
                "name": r.name,
                "metric": r.metric.value,
                "operator": r.operator.value,
                "threshold": r.threshold,
                "action_component_type": r.action_component_type.value,
                "action": r.action.value,
                "enabled": r.enabled,
                "description": r.description,
            }
            for r in scoped_rules
        ],
        "total": len(scoped_rules),
    }


# 工具分发表
_TOOL_DISPATCH: dict = {
    "get_latest_sensor_data": _tool_get_latest_sensor_data,
    "control_components_by_type": _tool_control_components_by_type,
    "get_group_components": _tool_get_group_components,
    "get_crop_status": _tool_get_crop_status,
    "list_pending_tasks": _tool_list_pending_tasks,
    "list_group_rules": _tool_list_group_rules,
}


# ---------------------------------------------------------------------------
# 核心分发器：call_tool
# ---------------------------------------------------------------------------

def call_tool(
    db: Session, device: DeviceContext, tool_name: str, arguments: dict
) -> dict:
    """MCP 工具调用分发器。

    流程：
    1. 校验工具名是否存在
    2. 计时执行工具（自动 scope 到 device.group_id）
    3. 写 McpCallLog（含 duration_ms + expires_at=now+30天）
    4. 返回结构化结果 {success, result, error, duration_ms}

    异常处理：捕获工具执行异常，记录 error_message，返回 success=False。
    """
    start = time.time()
    success = True
    result_data: dict | None = None
    error_msg: str | None = None

    if tool_name not in _TOOL_DISPATCH:
        success = False
        error_msg = f"Unknown tool: {tool_name}. Available: {list(_TOOL_DISPATCH.keys())}"
    else:
        try:
            handler = _TOOL_DISPATCH[tool_name]
            # 不同工具的参数签名不同，统一通过关键字参数传递
            if tool_name == "control_components_by_type":
                component_type = arguments.get("component_type")
                action = arguments.get("action")
                if not component_type or not action:
                    raise ValueError("Missing required arguments: component_type and action")
                result_data = handler(db, device, component_type=component_type, action=action)
            elif tool_name == "list_pending_tasks":
                limit = arguments.get("limit", 5)
                result_data = handler(db, device, limit=limit)
            elif tool_name == "list_group_rules":
                enabled_only = arguments.get("enabled_only", True)
                result_data = handler(db, device, enabled_only=enabled_only)
            else:
                # 无参数工具
                result_data = handler(db, device)
        except Exception as e:
            success = False
            error_msg = str(e)
            logger.exception("MCP tool '%s' execution failed", tool_name)

    duration_ms = int((time.time() - start) * 1000)

    # 写调用日志（不记对话原文，仅记工具名/参数/结果/耗时）
    try:
        log_entry = McpCallLog(
            group_id=device.group_id,
            device_token_id=device.token.id,
            tool_name=tool_name,
            arguments=json.dumps(arguments, ensure_ascii=False) if arguments else None,
            result=json.dumps(result_data, ensure_ascii=False) if result_data else None,
            duration_ms=duration_ms,
            success=success,
            error_message=error_msg,
            expires_at=datetime.now() + timedelta(days=LOG_RETENTION_DAYS),
        )
        db.add(log_entry)
        db.commit()
    except Exception:
        logger.exception("Failed to write MCP call log for tool '%s'", tool_name)
        db.rollback()

    return {
        "success": success,
        "result": result_data,
        "error": error_msg,
        "duration_ms": duration_ms,
    }


# ---------------------------------------------------------------------------
# 日志查询 + 过期清理
# ---------------------------------------------------------------------------

def list_logs(
    db: Session,
    group_id: int | None = None,
    tool_name: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[McpCallLog]:
    """查询 MCP 调用日志（按时间倒序）。"""
    stmt = select(McpCallLog)
    if group_id is not None:
        stmt = stmt.where(McpCallLog.group_id == group_id)
    if tool_name:
        stmt = stmt.where(McpCallLog.tool_name == tool_name)
    stmt = stmt.order_by(McpCallLog.created_at.desc()).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def cleanup_expired_mcp_logs(db: Session) -> int:
    """清理已过期的 MCP 调用日志（expires_at < now）。

    Returns:
        被清理的日志条数。
    """
    now = datetime.now()
    stmt = select(McpCallLog).where(McpCallLog.expires_at < now)
    expired = db.execute(stmt).scalars().all()
    count = len(expired)
    for log in expired:
        db.delete(log)
    if count > 0:
        db.commit()
        logger.info("Cleaned up %d expired MCP call logs", count)
    return count
