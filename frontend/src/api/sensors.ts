import { http } from './http'
import type { EChartsResponse, SensorData } from '@/types'

export async function fetchSensorData(params?: {
  node_id?: number
  start_time?: string
  end_time?: string
  limit?: number
}) {
  const { data } = await http.get<SensorData[]>('/sensors/data', { params })
  return data
}

export async function fetchLatestSensorData(nodeId?: number) {
  const { data } = await http.get<SensorData | null>('/sensors/data/latest', {
    params: nodeId ? { node_id: nodeId } : undefined,
  })
  return data
}

export async function fetchSensorCharts(params?: {
  node_id?: number
  start_time?: string
  end_time?: string
  limit?: number
  metrics?: string[]
}) {
  const { data } = await http.get<EChartsResponse>('/sensors/data/echarts', { params })
  return data
}
