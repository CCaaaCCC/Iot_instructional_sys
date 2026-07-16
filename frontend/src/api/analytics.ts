import { http } from './http'
import type {
  StudentStats,
  StudentAnalyticsFull,
  StudentAnalyticsSummary,
  StudentEChartsResponse,
  ClassroomOverview,
} from '@/types'

export async function fetchStudentsStats(params?: {
  group_id?: number
  classroom_id?: number
  skip?: number
  limit?: number
}) {
  const { data } = await http.get<StudentStats[]>('/analytics/students', { params })
  return data
}

export async function fetchStudentAnalytics(studentId: number) {
  const { data } = await http.get<StudentAnalyticsFull>(
    `/analytics/students/${studentId}`,
  )
  return data
}

export async function fetchStudentECharts(studentId: number) {
  const { data } = await http.get<StudentEChartsResponse>(
    `/analytics/students/${studentId}/echarts`,
  )
  return data
}

export async function fetchMyAnalytics() {
  const { data } = await http.get<StudentAnalyticsSummary | null>(
    '/student/me/analytics',
  )
  return data
}

export async function fetchClassroomOverview(classroomId: number) {
  const { data } = await http.get<ClassroomOverview>(
    `/analytics/classrooms/${classroomId}/overview`,
  )
  return data
}

export async function exportStudentGrowthPdf(studentId: number) {
  const res = await http.get(`/exports/students/${studentId}/growth-pdf`, {
    responseType: 'blob',
  })
  return res.data as Blob
}
