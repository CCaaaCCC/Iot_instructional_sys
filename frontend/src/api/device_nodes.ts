import { http } from './http'
import type {
  Component,
  ComponentStatus,
  ComponentType,
  DeviceNode,
  DeviceOperationLog,
} from '@/types'

export async function fetchNodes(params?: { online?: boolean }) {
  const { data } = await http.get<DeviceNode[]>('/device-nodes', { params })
  return data
}

export async function createNode(payload: { name: string; location?: string }) {
  const { data } = await http.post<DeviceNode>('/device-nodes', payload)
  return data
}

export async function updateNode(nodeId: number, payload: Partial<DeviceNode>) {
  const { data } = await http.patch<DeviceNode>(`/device-nodes/${nodeId}`, payload)
  return data
}

export async function deleteNode(nodeId: number) {
  await http.delete(`/device-nodes/${nodeId}`)
}

export async function fetchComponents(nodeId: number, params?: { component_type?: ComponentType }) {
  const { data } = await http.get<Component[]>(`/device-nodes/${nodeId}/components`, { params })
  return data
}

export async function createComponent(nodeId: number, payload: { name: string; type: ComponentType; metric?: string }) {
  const { data } = await http.post<Component>(`/device-nodes/${nodeId}/components`, payload)
  return data
}

export async function updateComponent(nodeId: number, componentId: number, payload: Partial<Component>) {
  const { data } = await http.patch<Component>(`/device-nodes/${nodeId}/components/${componentId}`, payload)
  return data
}

export async function controlComponent(
  nodeId: number,
  componentId: number,
  payload: { action: ComponentStatus; message?: string },
) {
  const { data } = await http.post<Component>(
    `/device-nodes/${nodeId}/components/${componentId}/control`,
    payload,
  )
  return data
}

export async function fetchNodeLogs(nodeId: number) {
  const { data } = await http.get<DeviceOperationLog[]>(`/device-nodes/${nodeId}/logs`)
  return data
}
