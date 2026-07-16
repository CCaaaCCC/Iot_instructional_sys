import { http } from './http'
import type { BatchStudentCreate, Group, User } from '@/types'

export async function fetchGroups(params?: { class_id?: number; node_id?: number }) {
  const { data } = await http.get<Group[]>('/groups', { params })
  return data
}

export async function createGroup(payload: { name: string; class_id: number; node_id?: number }) {
  const { data } = await http.post<Group>('/groups', payload)
  return data
}

export async function updateGroup(groupId: number, payload: Partial<Group>) {
  const { data } = await http.patch<Group>(`/groups/${groupId}`, payload)
  return data
}

export async function deleteGroup(groupId: number) {
  await http.delete(`/groups/${groupId}`)
}

export async function bindNode(groupId: number, nodeId: number) {
  const { data } = await http.post<Group>(`/groups/${groupId}/bind-node`, null, {
    params: { node_id: nodeId },
  })
  return data
}

export async function unbindNode(groupId: number) {
  const { data } = await http.post<Group>(`/groups/${groupId}/unbind-node`)
  return data
}

export async function fetchGroupStudents(groupId: number) {
  const { data } = await http.get<User[]>(`/groups/${groupId}/students`)
  return data
}

export async function batchCreateStudents(groupId: number, payload: BatchStudentCreate) {
  const { data } = await http.post<User[]>(`/groups/${groupId}/students/batch`, payload)
  return data
}
