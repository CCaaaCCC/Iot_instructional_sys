import { http } from './http'
import type { TeachingResource } from '@/types'

export async function fetchResources(params?: {
  classroom_id?: number
  group_id?: number
  subject?: string
  resource_type?: string
  skip?: number
  limit?: number
}) {
  const { data } = await http.get<TeachingResource[]>('/resources', { params })
  return data
}

export async function getResource(id: number) {
  const { data } = await http.get<TeachingResource>(`/resources/${id}`)
  return data
}

export async function createResource(formData: FormData) {
  const { data } = await http.post<TeachingResource>('/resources', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function updateResource(
  id: number,
  payload: Partial<TeachingResource>,
) {
  const { data } = await http.patch<TeachingResource>(
    `/resources/${id}`,
    payload,
  )
  return data
}

export async function deleteResource(id: number) {
  await http.delete(`/resources/${id}`)
}

export async function togglePublishResource(id: number) {
  const { data } = await http.patch<TeachingResource>(
    `/resources/${id}/publish`,
  )
  return data
}

export async function fetchMyResources() {
  const { data } = await http.get<TeachingResource[]>('/student/me/resources')
  return data
}
