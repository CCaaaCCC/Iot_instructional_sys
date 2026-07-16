import { http } from './http'
import type { ClassTask, EChartsResponse, Experiment, ExperimentGroup, ExperimentObservation, Group, SensorData, SensorMetric, TaskSubmission, User } from '@/types'

export async function fetchMyGroup() {
  const { data } = await http.get<Group | null>('/student/me/group')
  return data
}

export async function fetchMyTasks() {
  const { data } = await http.get<ClassTask[]>('/student/me/tasks')
  return data
}

export async function fetchMySubmissions(taskId?: number) {
  const { data } = await http.get<TaskSubmission[]>('/student/me/submissions', {
    params: taskId ? { task_id: taskId } : undefined,
  })
  return data
}

export async function fetchMySensorData(limit = 50) {
  const { data } = await http.get<SensorData[]>('/student/me/sensor-data', {
    params: { limit },
  })
  return data
}

export async function fetchMyLatestSensorData() {
  const { data } = await http.get<SensorData | null>('/student/me/sensor-data/latest')
  return data
}

export async function fetchMySensorECharts(metrics?: SensorMetric[], limit = 200) {
  const { data } = await http.get<EChartsResponse>('/student/me/sensor-data/echarts', {
    params: {
      limit,
      ...(metrics && metrics.length > 0 ? { metrics } : {}),
    },
  })
  return data
}

export async function submitMyTask(taskId: number, formData: FormData) {
  const { data } = await http.post<TaskSubmission>(
    `/student/me/tasks/${taskId}/submit`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

export async function updateMyProfile(payload: { display_name?: string; avatar_url?: string }) {
  const { data } = await http.patch<User>('/student/me/profile', payload)
  return data
}

export async function changeMyPassword(oldPassword: string, newPassword: string) {
  const { data } = await http.patch<User>('/student/me/password', {
    old_password: oldPassword,
    new_password: newPassword,
  })
  return data
}

export async function uploadMyAvatar(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await http.post<{ avatar_url: string }>('/student/me/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// ---- Student Experiment APIs ----
export async function fetchMyExperiments() {
  const { data } = await http.get<Experiment[]>('/student/me/experiments')
  return data
}

export async function getMyExperiment(id: number) {
  const { data } = await http.get<Experiment>(`/student/me/experiments/${id}`)
  return data
}

export async function fetchMyExperimentObservations(experimentId: number) {
  const { data } = await http.get<ExperimentObservation[]>(`/student/me/experiments/${experimentId}/observations`)
  return data
}

export async function createMyExperimentObservation(experimentId: number, payload: { sensor_data_id?: number | null; content?: string | null }) {
  const { data } = await http.post<ExperimentObservation>(`/student/me/experiments/${experimentId}/observations`, payload)
  return data
}

export async function fetchMyExperimentGroup(experimentId: number) {
  const { data } = await http.get<ExperimentGroup | null>(`/student/me/experiments/${experimentId}/group`)
  return data
}
