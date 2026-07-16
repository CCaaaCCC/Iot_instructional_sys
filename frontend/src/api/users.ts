import { http } from './http'
import type { User } from '@/types'

export async function fetchUsers() {
  const { data } = await http.get<User[]>('/users')
  return data
}

export async function createUser(payload: Partial<User> & { password: string }) {
  const { data } = await http.post<User>('/users', payload)
  return data
}

export async function updateUser(userId: number, payload: Partial<User> & { password?: string }) {
  const { data } = await http.patch<User>(`/users/${userId}`, payload)
  return data
}

export async function deleteUser(userId: number) {
  await http.delete(`/users/${userId}`)
}
