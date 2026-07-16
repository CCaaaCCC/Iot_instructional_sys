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

export async function createSensorData(payload: {
  node_id: number
  air_temp?: number | null
  air_humidity?: number | null
  soil_temp?: number | null
  soil_humidity?: number | null
  light_intensity?: number | null
  soil_ph?: number | null
  recorded_at?: string | null
}) {
  const { data } = await http.post<SensorData>('/sensors/data', payload)
  return data
}
