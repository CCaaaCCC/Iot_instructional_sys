import { http } from './http'
import type { Crop } from '@/types'

export async function fetchCrops() {
  const { data } = await http.get<Crop[]>('/crops')
  return data
}

export async function createCrop(payload: Partial<Crop>) {
  const { data } = await http.post<Crop>('/crops', payload)
  return data
}

export async function updateCrop(cropId: number, payload: Partial<Crop>) {
  const { data } = await http.patch<Crop>(`/crops/${cropId}`, payload)
  return data
}

export async function deleteCrop(cropId: number) {
  await http.delete(`/crops/${cropId}`)
}
