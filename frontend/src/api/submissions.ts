import { http } from './http'
import type { TaskSubmission } from '@/types'

export async function fetchSubmissions(params?: {
  task_id?: number
  student_id?: number
  reviewed?: boolean
}) {
  const { data } = await http.get<TaskSubmission[]>('/submissions', { params })
  return data
}

export async function getSubmission(submissionId: number) {
  const { data } = await http.get<TaskSubmission>(`/submissions/${submissionId}`)
  return data
}

export async function submitTask(taskId: number, formData: FormData) {
  const { data } = await http.post<TaskSubmission>('/submissions', formData, {
    params: { task_id: taskId },
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function reviewSubmission(
  submissionId: number,
  payload: { score: number; feedback?: string },
) {
  const { data } = await http.post<TaskSubmission>(
    `/submissions/${submissionId}/review`,
    payload,
  )
  return data
}
