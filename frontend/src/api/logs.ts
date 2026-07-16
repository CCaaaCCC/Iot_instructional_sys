import { http } from './http'
import type { DeviceOperationLog, OperationLog, RuleLog } from '@/types'

export async function fetchOperationLogs(params?: { user_id?: number; entity_type?: string; start_time?: string; end_time?: string }) {
  const { data } = await http.get<OperationLog[]>('/logs/operations', { params })
  return data
}

export async function fetchDeviceLogs(params?: { node_id?: number; component_id?: number }) {
  const { data } = await http.get<DeviceOperationLog[]>('/logs/device', { params })
  return data
}

export async function fetchRuleLogs(params?: { rule_id?: number }) {
  const { data } = await http.get<RuleLog[]>('/logs/rules', { params })
  return data
}
