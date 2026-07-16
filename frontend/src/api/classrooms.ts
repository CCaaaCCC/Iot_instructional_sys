import { http } from './http'
import type { Classroom, CourseSubject } from '@/types'

export async function fetchClassrooms(params?: { teacher_id?: number; subject?: CourseSubject }) {
  const { data } = await http.get<Classroom[]>('/classrooms', { params })
  return data
}

export async function createClassroom(payload: { name: string; subject: CourseSubject; teacher_id?: number }) {
  const { data } = await http.post<Classroom>('/classrooms', payload)
  return data
}

export async function updateClassroom(classroomId: number, payload: Partial<Classroom>) {
  const { data } = await http.patch<Classroom>(`/classrooms/${classroomId}`, payload)
  return data
}

export async function deleteClassroom(classroomId: number) {
  await http.delete(`/classrooms/${classroomId}`)
}
