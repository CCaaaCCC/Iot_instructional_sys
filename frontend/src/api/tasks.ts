import { http } from './http'
import type { ClassTask } from '@/types'

export async function fetchTasks(params?: { group_id?: number }) {
  const { data } = await http.get<ClassTask[]>('/tasks', { params })
  return data
}

export async function getTask(taskId: number) {
  const { data } = await http.get<ClassTask>(`/tasks/${taskId}`)
  return data
}

export async function createTask(payload: Partial<ClassTask>) {
  const { data } = await http.post<ClassTask>('/tasks', payload)
  return data
}

export async function updateTask(taskId: number, payload: Partial<ClassTask>) {
  const { data } = await http.patch<ClassTask>(`/tasks/${taskId}`, payload)
  return data
}

export async function deleteTask(taskId: number) {
  await http.delete(`/tasks/${taskId}`)
}
