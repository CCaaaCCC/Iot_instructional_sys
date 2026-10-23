<template>
  <div class="content-area">
    <div v-if="loading" class="content-area">
      <div v-for="i in 3" :key="i" class="skeleton card"></div>
    </div>
    <div v-else-if="error" class="msg-error" style="margin-bottom: 12px">{{ error }}</div>
    <template v-else>
      <div class="realtime-banner" v-if="connected">
        <span class="badge success"><span class="badge-dot"></span> 实时连接中</span>
        <span class="banner-hint">本组 ESP32-CAM 新上传的诊断会自动出现在顶部</span>
      </div>

      <EmptyState
        v-if="diagnoses.length === 0"
        icon="camera"
        title="暂无诊断记录"
        desc="等待本组 ESP32-CAM 上传植物照片"
      />
      <div v-else class="diagnosis-grid">
        <article
          v-for="d in diagnoses"
          :key="d.id"
          class="content-card diagnosis-card"
        >
          <div class="diagnosis-image-wrap" @click="previewImage = d.image_url">
            <img :src="d.image_url" :alt="resultLabel(d.diagnosis_result)" class="diagnosis-image" />
            <div class="diagnosis-image-overlay">点击查看大图</div>
          </div>

          <div class="diagnosis-body">
            <div class="task-card-header">
              <h3 class="card-title">诊断 #{{ d.id }}</h3>
              <div class="task-badges">
                <span class="badge" :class="isHealthy(d.diagnosis_result) ? 'success' : 'danger'">
                  <span class="badge-dot"></span> {{ resultLabel(d.diagnosis_result) }}
                </span>
              </div>
            </div>

            <div class="diagnosis-meta">
              <div class="meta-item">
                <span class="meta-label">置信度</span>
                <div class="confidence-bar">
                  <div class="confidence-fill" :class="isHealthy(d.diagnosis_result) ? 'healthy' : 'disease'" :style="{ width: (d.confidence * 100) + '%' }"></div>
                </div>
                <span class="confidence-value">{{ (d.confidence * 100).toFixed(1) }}%</span>
              </div>
            </div>

            <div v-if="d.suggestion" class="task-description">
              <strong>处理建议：</strong>{{ d.suggestion }}
            </div>

            <div class="task-meta-row">
              <span class="meta-item">时间：{{ formatTime(d.created_at) }}</span>
              <span v-if="d.node_name" class="meta-item">节点：{{ d.node_name }}</span>
            </div>
          </div>
        </article>
      </div>
    </template>

    <Teleport to="body">
      <div v-if="previewImage" class="image-modal" @click="previewImage = null">
        <img :src="previewImage" class="modal-image" />
        <div class="modal-hint">点击任意处关闭</div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import EmptyState from '@/components/EmptyState.vue'
import { fetchMyPestDiagnoses } from '@/api/pest_diagnosis'
import { useWebSocket } from '@/composables/useWebSocket'
import type { DiagnosisResult, PestDiagnosisListItem } from '@/types'

const { connected, pestDiagnoses } = useWebSocket()

const loading = ref(true)
const error = ref('')
const diagnoses = ref<PestDiagnosisListItem[]>([])
const previewImage = ref<string | null>(null)

const resultLabels: Record<DiagnosisResult, string> = {
  tomato_healthy: '番茄健康',
  tomato_early_blight: '番茄早疫病',
  tomato_late_blight: '番茄晚疫病',
  strawberry_healthy: '草莓健康',
  strawberry_leaf_scorch: '草莓叶焦病',
}

function resultLabel(result: string): string {
  return resultLabels[result as DiagnosisResult] ?? result
}

function isHealthy(result: string): boolean {
  return result.endsWith('_healthy')
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleString('zh-CN') : '-'
}

async function loadDiagnoses() {
  loading.value = true
  error.value = ''
  try {
    diagnoses.value = await fetchMyPestDiagnoses(50)
  } catch (err) {
    error.value = '诊断记录加载失败，请确认后端已启动。'
    console.error('Failed to load pest diagnoses:', err)
  } finally {
    loading.value = false
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

onMounted(loadDiagnoses)
</script>

<style scoped>
.realtime-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  margin-bottom: 16px;
  background: var(--panel-hover);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.banner-hint {
  font-size: 13px;
  color: var(--muted);
}
.diagnosis-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.diagnosis-card {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.diagnosis-image-wrap {
  position: relative;
  width: 100%;
  height: 180px;
  cursor: pointer;
  overflow: hidden;
  background: var(--bg-elevated);
}
.diagnosis-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.25s;
}
.diagnosis-image-wrap:hover .diagnosis-image {
  transform: scale(1.05);
}
.diagnosis-image-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 6px 10px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.6));
  color: #fff;
  font-size: 12px;
  text-align: center;
  opacity: 0;
  transition: opacity 0.2s;
}
.diagnosis-image-wrap:hover .diagnosis-image-overlay {
  opacity: 1;
}
.diagnosis-body {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.diagnosis-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--muted);
}
.meta-label {
  font-size: 12px;
  color: var(--muted);
  min-width: 50px;
}
.confidence-bar {
  flex: 1;
  height: 6px;
  background: var(--line);
  border-radius: 3px;
  overflow: hidden;
}
.confidence-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s;
}
.confidence-fill.healthy {
  background: var(--primary);
}
.confidence-fill.disease {
  background: var(--danger);
}
.confidence-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  min-width: 44px;
  text-align: right;
}
.image-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  cursor: pointer;
}
.modal-image {
  max-width: 85%;
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
  padding: 60px 20px;
  text-align: center;
  color: var(--muted);
}
.empty-state-icon {
  font-size: 40px;
  margin-bottom: 10px;
}
</style>
