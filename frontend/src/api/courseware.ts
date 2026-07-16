import { http } from './http'
import type { Courseware } from '@/types'

export async function fetchMyCourseware(params?: {
  file_type?: string
  subject?: string
  skip?: number
  limit?: number
}) {
  const { data } = await http.get<Courseware[]>('/courseware/my', { params })
  return data
}

export async function fetchPublicCourseware(params?: {
  file_type?: string
  subject?: string
  grade_level?: string
  search?: string
  skip?: number
  limit?: number
}) {
  const { data } = await http.get<Courseware[]>('/courseware/public', { params })
  return data
}

export async function getCourseware(id: number) {
  const { data } = await http.get<Courseware>(`/courseware/${id}`)
  return data
}

export async function createCourseware(formData: FormData) {
  const { data } = await http.post<Courseware>('/courseware', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function updateCourseware(
  id: number,
  payload: Partial<Courseware>,
) {
  const { data } = await http.patch<Courseware>(`/courseware/${id}`, payload)
  return data
}

export async function deleteCourseware(id: number) {
  await http.delete(`/courseware/${id}`)
}

export async function toggleCoursewarePublic(id: number) {
  const { data } = await http.patch<Courseware>(
    `/courseware/${id}/toggle-public`,
  )
  return data
}
