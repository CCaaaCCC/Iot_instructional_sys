"""MCP 路由：小智 AI（ESP32-S3）工具调用接口。

权限：
- GET /mcp/tools + POST /mcp/tools/call：设备 token 鉴权（get_device_context）
- GET /mcp/logs：用户 token 鉴权，仅 admin + teacher（教师可读所有班级）
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.core.device_auth import DeviceContext, get_device_context
from app.models.enums import UserRole
from app.schemas.mcp import (
    McpCallLogListOut,
    McpToolCallRequest,
    McpToolCallResponse,
    McpToolDefinition,
)
from app.services import mcp_service

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/tools", response_model=list[McpToolDefinition])
def list_tools(
    device: DeviceContext = Depends(get_device_context),
) -> list[McpToolDefinition]:
    """返回 MCP 工具清单（设备 token 鉴权）。

    供小智 AI 客户端启动时拉取能力列表，了解可调用的工具及其参数。
    """
    tools = mcp_service.list_tools()
    return [
        McpToolDefinition(
            name=t["name"],
            description=t["description"],
            parameters=t.get("parameters", {}),
        )
        for t in tools
    ]


@router.post("/tools/call", response_model=McpToolCallResponse)
def call_tool(
    payload: McpToolCallRequest,
    db: Session = Depends(get_db),
    device: DeviceContext = Depends(get_device_context),
) -> McpToolCallResponse:
    """调用 MCP 工具（设备 token 鉴权）。

    核心安全：所有工具自动 scope 到 device.group_id，不接受外部传入 group_id。
    返回结构化结果 {success, result, error, duration_ms}。
    """
    result = mcp_service.call_tool(
        db,
        device=device,
        tool_name=payload.tool_name,
        arguments=payload.arguments,
    )
    return McpToolCallResponse(
        success=result["success"],
        result=result["result"],
        error=result["error"],
        duration_ms=result["duration_ms"],
    )


@router.get("/logs", response_model=list[McpCallLogListOut])
def list_logs(
    group_id: int | None = None,
    tool_name: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher, UserRole.operator)),
) -> list[McpCallLogListOut]:
    """查询 MCP 调用日志（admin + teacher + operator，教师可读所有班级）。

    支持按 group_id 和 tool_name 过滤，按时间倒序返回。
    """
    logs = mcp_service.list_logs(
        db, group_id=group_id, tool_name=tool_name, skip=skip, limit=limit
    )
    result: list[McpCallLogListOut] = []
    for log in logs:
        group_name = log.group.name if log.group else None
        result.append(
            McpCallLogListOut(
                id=log.id,
                group_id=log.group_id,
                device_token_id=log.device_token_id,
                tool_name=log.tool_name,
                arguments=log.arguments,
                result=log.result,
                duration_ms=log.duration_ms,
                success=log.success,
                error_message=log.error_message,
                created_at=log.created_at,
                expires_at=log.expires_at,
                group_name=group_name,
            )
        )
    return result
