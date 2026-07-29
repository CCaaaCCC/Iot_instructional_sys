<template>
  <div class="grid" style="gap: 18px">
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">病虫害诊断记录</h3>
          <div class="card-subtitle">ESP32-CAM 视觉节点上传的植物照片经 AI 诊断后的结果（教师可查看所有班级）</div>
        </div>
        <div class="toolbar">
          <select v-model="filters.group_id" class="select" style="width: 140px" @change="loadDiagnoses">
            <option value="">全部小组</option>
            <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
          <select v-model="filters.diagnosis_result" class="select" style="width: 180px" @change="loadDiagnoses">
            <option value="">全部结果</option>
            <option v-for="r in resultOptions" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
          <button class="btn secondary sm" @click="loadDiagnoses">刷新</button>
          <span v-if="connected" class="badge success" style="margin-left:8px"><span class="badge-dot"></span> 实时</span>
        </div>
      </template>

      <div v-if="error" class="msg-error">{{ error }}</div>

      <div v-if="!diagnoses.length" class="empty-state">
        暂无诊断记录
      </div>

      <table v-else class="table">
        <thead>
          <tr>
            <th>照片</th>
            <th>诊断结果</th>
            <th>置信度</th>
            <th>小组</th>
            <th>处理建议</th>
            <th>时间</th>
            <th v-if="isAdmin">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in diagnoses" :key="d.id">
            <td>
              <img
                :src="d.image_url"
                :alt="d.diagnosis_result"
                class="thumb"
                @click="previewImage = d.image_url"
              />
            </td>
            <td>
              <span class="badge" :class="isHealthy(d.diagnosis_result) ? 'success' : 'danger'">
                <span class="badge-dot"></span> {{ resultLabel(d.diagnosis_result) }}
              </span>
            </td>
            <td>{{ (d.confidence * 100).toFixed(1) }}%</td>
            <td>{{ d.group_name || '#' + d.group_id }}</td>
            <td class="suggestion-cell">{{ d.suggestion || '-' }}</td>
            <td>{{ formatTime(d.created_at) }}</td>
            <td v-if="isAdmin">
              <button class="btn danger sm" @click="handleDelete(d.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </SectionCard>

    <div v-if="previewImage" class="image-modal" @click="previewImage = null">
      <img :src="previewImage" class="modal-image" />
      <div class="modal-hint">点击任意处关闭</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch, computed } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import { fetchPestDiagnoses, deletePestDiagnosis } from '@/api/pest_diagnosis'
import { fetchGroups } from '@/api/groups'
import { useAuthStore } from '@/stores/auth'
import { useWebSocket } from '@/composables/useWebSocket'
import type { DiagnosisResult, Group, PestDiagnosisListItem } from '@/types'

const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'admin')

const { connected, pestDiagnoses } = useWebSocket()

const diagnoses = ref<PestDiagnosisListItem[]>([])
const groups = ref<Group[]>([])
const error = ref('')
const previewImage = ref<string | null>(null)

const filters = reactive({
  group_id: '' as string | number,
  diagnosis_result: '' as string,
})

const resultOptions: { value: DiagnosisResult; label: string }[] = [
  { value: 'tomato_healthy', label: '番茄健康' },
  { value: 'tomato_early_blight', label: '番茄早疫病' },
  { value: 'tomato_late_blight', label: '番茄晚疫病' },
  { value: 'strawberry_healthy', label: '草莓健康' },
  { value: 'strawberry_leaf_scorch', label: '草莓叶焦病' },
]

function resultLabel(result: string): string {
  const opt = resultOptions.find((o) => o.value === result)
  return opt ? opt.label : result
}

function isHealthy(result: string): boolean {
  return result.endsWith('_healthy')
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleString('zh-CN') : '-'
}

async function loadDiagnoses() {
  error.value = ''
  try {
    const params: { group_id?: number; diagnosis_result?: DiagnosisResult } = {}
    if (filters.group_id) params.group_id = Number(filters.group_id)
    if (filters.diagnosis_result) params.diagnosis_result = filters.diagnosis_result as DiagnosisResult
    diagnoses.value = await fetchPestDiagnoses(params)
  } catch {
    error.value = '诊断记录加载失败，请确认后端已启动。'
  }
}

async function handleDelete(id: number) {
  if (!confirm(`确认删除诊断记录 #${id}？图片将一并删除。`)) return
  try {
    await deletePestDiagnosis(id)
    diagnoses.value = diagnoses.value.filter((d) => d.id !== id)
  } catch {
    error.value = '删除失败（仅管理员可删除）。'
  }
}

// WebSocket 实时更新：新诊断插入到列表顶部
watch(pestDiagnoses, (events) => {
  const latest = events[events.length - 1]
  if (!latest) return
  // 避免重复添加
  if (diagnoses.value.some((d) => d.id === latest.id)) return
  // 插入到顶部
  diagnoses.value.unshift({
    id: latest.id,
    group_id: latest.group_id,
    node_id: latest.node_id,
    device_token_id: 0,
    image_url: latest.image_url,
    diagnosis_result: latest.diagnosis_result as DiagnosisResult,
    confidence: latest.confidence,
    suggestion: latest.suggestion,
    created_at: latest.created_at || new Date().toISOString(),
    group_name: null,
    node_name: null,
  })
})

onMounted(async () => {
  await loadDiagnoses()
  try {
    groups.value = await fetchGroups()
  } catch {
    // 忽略
  }
})
</script>

<style scoped>
.thumb {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid var(--line);
  transition: transform 0.15s;
}
.thumb:hover {
  transform: scale(1.1);
}
.suggestion-cell {
  max-width: 280px;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.5;
}
.image-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  cursor: pointer;
}
.modal-image {
  max-width: 80%;
  max-height: 80%;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}
.modal-hint {
  color: #fff;
  margin-top: 16px;
  font-size: 14px;
  opacity: 0.7;
}
.empty-state {
  padding: 40px;
  text-align: center;
  color: var(--muted);
}
.empty-state-icon {
  font-size: 36px;
  margin-bottom: 8px;
}
</style>
