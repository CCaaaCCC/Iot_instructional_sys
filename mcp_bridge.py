"""智慧大棚 MCP 桥接程序（直接 WebSocket 连接小智后台）。

实现标准 MCP 协议（JSON-RPC 2.0）over WebSocket，
将小智后台的工具调用请求转发到本地后端 API。

架构：
    小智后台 (WebSocket) ←→ 本文件 (MCP JSON-RPC 2.0) ←→ 本地后端 API (HTTP)

环境变量：
    MCP_ENDPOINT  - 小智后台 MCP 接入点（完整 WebSocket URL，从 xiaozhi.me 控制台获取）
    DEVICE_TOKEN  - 设备 token（从后台 /device-tokens 获取 esp32s3 类型）
    LOCAL_API_BASE - 本地后端地址，默认 http://127.0.0.1:8001

使用方式：
    1. 设置环境变量 MCP_ENDPOINT 和 DEVICE_TOKEN
    2. 确保后端服务已启动
    3. python mcp_bridge.py
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any

import httpx
import websockets
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mcp_bridge.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

MCP_ENDPOINT = os.getenv("MCP_ENDPOINT", "")
DEVICE_TOKEN = os.getenv("DEVICE_TOKEN", "")
LOCAL_API_BASE = os.getenv("LOCAL_API_BASE", "http://127.0.0.1:8001")
RECONNECT_DELAY = 5
MAX_RECONNECT_DELAY = 60

# MCP 协议版本
PROTOCOL_VERSION = "2024-11-05"

# ---------------------------------------------------------------------------
# 工具定义（标准 MCP 格式，inputSchema 使用 JSON Schema）
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_latest_sensor_data",
        "description": "获取本组的最新环境数据（气温、湿度、土壤温湿度、光照、pH）",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "control_components_by_type",
        "description": "按类型控制本组所有执行器（如'打开风扇'会控制本组所有风扇）。类型可选: fan/pump/light",
        "inputSchema": {
            "type": "object",
            "properties": {
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
            "required": ["component_type", "action"],
        },
    },
    {
        "name": "get_group_components",
        "description": "查询本组所有执行器（风扇/水泵/补光灯）的当前状态",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_crop_status",
        "description": "查询本组的作物生长状态",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_pending_tasks",
        "description": "列出本组的未完成课堂任务",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "返回条数上限，默认 5",
                    "default": 5,
                }
            },
            "required": [],
        },
    },
    {
        "name": "list_group_rules",
        "description": "查询本组节点启用的自动控制规则",
        "inputSchema": {
            "type": "object",
            "properties": {
                "enabled_only": {
                    "type": "boolean",
                    "description": "是否仅返回启用的规则，默认 true",
                    "default": True,
                }
            },
            "required": [],
        },
    },
]


# ---------------------------------------------------------------------------
# 调用本地后端 API（带设备 token 鉴权）
# ---------------------------------------------------------------------------


async def call_local_tool(tool_name: str, arguments: dict) -> dict:
    """通过 HTTP 调用本地后端 MCP 工具（带设备 token 鉴权）。"""
    headers = {"Authorization": f"Bearer {DEVICE_TOKEN}"}
    payload = {"tool_name": tool_name, "arguments": arguments}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{LOCAL_API_BASE}/api/v1/mcp/tools/call",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"调用本地工具 {tool_name} 失败: HTTP {e.response.status_code} - {e.response.text}"
        )
        return {
            "success": False,
            "error": f"HTTP {e.response.status_code}: {e.response.text}",
        }
    except Exception as e:
        logger.error(f"调用本地工具 {tool_name} 异常: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# MCP 协议消息处理（JSON-RPC 2.0）
# ---------------------------------------------------------------------------


def make_response(msg_id: Any, result: dict) -> str:
    """构造 JSON-RPC 2.0 成功响应。"""
    return json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}, ensure_ascii=False)


def make_error(msg_id: Any, code: int, message: str) -> str:
    """构造 JSON-RPC 2.0 错误响应。"""
    return json.dumps(
        {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}},
        ensure_ascii=False,
    )


async def handle_mcp_message(ws, message: str):
    """处理来自小智后台的 MCP JSON-RPC 2.0 消息。"""
    data = None
    try:
        data = json.loads(message)
        method = data.get("method")
        msg_id = data.get("id")

        # 通知（无 id，无需响应）
        if msg_id is None:
            logger.info(f"收到通知: {method}")
            return

        logger.info(f"收到请求: method={method}, id={msg_id}")

        # 1. initialize - 握手
        if method == "initialize":
            response = make_response(
                msg_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "greenhouse-mcp", "version": "1.0.0"},
                },
            )
            await ws.send(response)
            logger.info("已响应 initialize")

        # 2. tools/list - 返回工具清单
        elif method == "tools/list":
            response = make_response(msg_id, {"tools": TOOLS})
            await ws.send(response)
            logger.info(f"已响应 tools/list: {len(TOOLS)} 个工具")

        # 2.5. ping - 保持连接心跳（JSON-RPC 2.0 标准方法）
        elif method == "ping":
            response = make_response(msg_id, {})
            await ws.send(response)
            logger.debug("已响应 ping")

        # 3. tools/call - 调用工具
        elif method == "tools/call":
            params = data.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            logger.info(f"调用工具: {tool_name}, 参数: {arguments}")

            result = await call_local_tool(tool_name, arguments)
            success = result.get("success", False)
            result_data = result.get("result") or result.get("error", "unknown error")

            # MCP 标准返回格式：content 数组 + isError 标志
            response = make_response(
                msg_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result_data, ensure_ascii=False),
                        }
                    ],
                    "isError": not success,
                },
            )
            await ws.send(response)
            logger.info(f"工具调用完成: {tool_name}, success={success}")

        else:
            logger.warning(f"未知方法: {method}")
            await ws.send(make_error(msg_id, -32601, f"Method not found: {method}"))

    except json.JSONDecodeError:
        logger.error(f"消息解析失败: {message[:100]}...")
    except Exception as e:
        logger.error(f"处理消息失败: {e}", exc_info=True)
        if data is not None and data.get("id") is not None:
            await ws.send(make_error(data["id"], -32603, f"Internal error: {e}"))


# ---------------------------------------------------------------------------
# WebSocket 连接 + 重连
# ---------------------------------------------------------------------------


async def mcp_bridge():
    """连接小智后台 WebSocket，处理 MCP 协议消息。"""
    if not MCP_ENDPOINT:
        logger.error("MCP_ENDPOINT 环境变量未设置！")
        logger.error("请从 xiaozhi.me 控制台获取 MCP 接入点（完整 WebSocket URL）")
        sys.exit(1)

    if not DEVICE_TOKEN:
        logger.error("DEVICE_TOKEN 环境变量未设置！")
        logger.error("请从后台 /device-tokens 获取 esp32s3 类型的 token")
        sys.exit(1)

    reconnect_delay = RECONNECT_DELAY

    while True:
        logger.info(f"正在连接小智 MCP 服务: {MCP_ENDPOINT}")
        try:
            async with websockets.connect(MCP_ENDPOINT, ping_interval=30) as ws:
                logger.info("✅ 成功连接到小智 MCP 服务！")
                reconnect_delay = RECONNECT_DELAY

                async for message in ws:
                    await handle_mcp_message(ws, message)

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"连接关闭: code={e.code}, reason={e.reason}")
        except Exception as e:
            logger.error(f"连接失败: {e}")

        logger.info(f"{reconnect_delay} 秒后重新连接...")
        await asyncio.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY)


if __name__ == "__main__":
    if not MCP_ENDPOINT:
        print("❌ 请设置 MCP_ENDPOINT 环境变量（完整 WebSocket URL）")
        print("示例: wss://api.xiaozhi.me/mcp/your-endpoint")
        sys.exit(1)

    if not DEVICE_TOKEN:
        print("❌ 请设置 DEVICE_TOKEN 环境变量")
        print("从后台 /device-tokens 获取 esp32s3 类型的 token")
        sys.exit(1)

    print("🚀 启动小智 MCP 桥接程序")
    print(f"📡 连接地址: {MCP_ENDPOINT}")
    print(f"🔌 本地 API: {LOCAL_API_BASE}")
    print(f"🔑 设备 Token: {DEVICE_TOKEN[:8]}...")
    print()

    try:
        asyncio.run(mcp_bridge())
    except KeyboardInterrupt:
        logger.info("收到中断信号，退出程序")
        sys.exit(0)
