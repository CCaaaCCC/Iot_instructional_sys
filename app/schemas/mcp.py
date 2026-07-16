"""MCP（Model Context Protocol）相关 schema。

小智 AI（ESP32-S3）通过 MCP 协议调用后端工具，
工具集为最小集（读 + 控制），全部自动 scope 到 device_context.group_id。
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class McpToolParameter(BaseModel):
    """工具参数定义（JSON Schema 风格的简化版）。"""

    type: str = Field(..., description="参数类型：string/integer/boolean")
    description: str = Field(..., description="参数描述")
    enum: list[str] | None = Field(None, description="枚举可选值")
    default: Any | None = Field(None, description="默认值")


class McpToolDefinition(BaseModel):
    """MCP 工具定义，供小智 AI 解析能力。"""

    name: str
    description: str
    parameters: dict[str, McpToolParameter] = Field(
        default_factory=dict, description="参数 Schema，空对象表示无参数"
    )


class McpToolCallRequest(BaseModel):
    """工具调用请求体。"""

    tool_name: str = Field(..., description="工具名")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="工具参数（JSON 对象）"
    )


class McpToolCallResponse(BaseModel):
    """工具调用响应。"""

    success: bool
    result: dict[str, Any] | None = Field(None, description="调用结果（成功时）")
    error: str | None = Field(None, description="错误信息（失败时）")
    duration_ms: int = Field(..., description="调用耗时（毫秒）")


class McpCallLogOut(BaseModel):
    """MCP 调用日志输出。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    device_token_id: int
    tool_name: str
    arguments: str | None
    result: str | None
    duration_ms: int
    success: bool
    error_message: str | None
    created_at: datetime
    expires_at: datetime


class McpCallLogListOut(McpCallLogOut):
    """MCP 调用日志列表项（含小组名）。"""

    group_name: str | None = None
