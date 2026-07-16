import { http } from './http'
import type { DeviceToken, DeviceTokenListItem, DeviceTokenWithSecret, DeviceType } from '@/types'

export async function fetchDeviceTokens(params?: {
  group_id?: number
  device_type?: DeviceType
  is_active?: boolean
}) {
  const { data } = await http.get<DeviceTokenListItem[]>('/device-tokens', { params })
  return data
}

export async function createDeviceToken(payload: {
  group_id: number
  device_type: DeviceType
  device_name: string
  node_id: number
}) {
  const { data } = await http.post<DeviceTokenWithSecret>('/device-tokens', payload)
  return data
}

export async function resetDeviceToken(tokenId: number) {
  const { data } = await http.post<DeviceTokenWithSecret>(`/device-tokens/${tokenId}/reset`)
  return data
}

export async function revokeDeviceToken(tokenId: number) {
  const { data } = await http.post<DeviceToken>(`/device-tokens/${tokenId}/revoke`)
  return data
}

export async function deleteDeviceToken(tokenId: number) {
  await http.delete(`/device-tokens/${tokenId}`)
}
