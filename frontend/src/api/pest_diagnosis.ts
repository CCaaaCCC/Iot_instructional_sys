import { http } from './http'
import type { DiagnosisResult, PestDiagnosisListItem } from '@/types'

export async function fetchPestDiagnoses(params?: {
  group_id?: number
  diagnosis_result?: DiagnosisResult
}) {
  const { data } = await http.get<PestDiagnosisListItem[]>('/pest-diagnoses', { params })
  return data
}

export async function fetchPestDiagnosisDetail(id: number) {
  const { data } = await http.get<PestDiagnosisListItem>(`/pest-diagnoses/${id}`)
  return data
}

export async function deletePestDiagnosis(id: number) {
  await http.delete(`/pest-diagnoses/${id}`)
}

// ---- 学生端 ----
export async function fetchMyPestDiagnoses(limit: number = 50) {
  const { data } = await http.get<PestDiagnosisListItem[]>('/student/me/pest-diagnoses', {
    params: { limit },
  })
  return data
}
