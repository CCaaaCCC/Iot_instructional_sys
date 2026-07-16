import { http } from './http'
import type { McpToolDefinition, McpToolCallResponse, McpCallLogListItem } from '@/types'

/** 获取 MCP 工具清单（需设备 token，但管理端展示用 admin token 也能调通展示 schema） */
export async function fetchMcpTools(deviceToken?: string) {
  const headers: Record<string, string> = {}
  if (deviceToken) {
    headers.Authorization = `Bearer ${deviceToken}`
  }
  const { data } = await http.get<McpToolDefinition[]>('/mcp/tools', { headers })
  return data
}

/** 调用 MCP 工具（需设备 token） */
export async function callMcpTool(
  toolName: string,
  arguments_: Record<string, unknown>,
  deviceToken: string,
) {
  const { data } = await http.post<McpToolCallResponse>(
    '/mcp/tools/call',
    { tool_name: toolName, arguments: arguments_ },
    { headers: { Authorization: `Bearer ${deviceToken}` } },
  )
  return data
}

/** 查询 MCP 调用日志（admin/teacher/operator） */
export async function fetchMcpLogs(params?: {
  group_id?: number
  tool_name?: string
}) {
  const { data } = await http.get<McpCallLogListItem[]>('/mcp/logs', { params })
  return data
}
