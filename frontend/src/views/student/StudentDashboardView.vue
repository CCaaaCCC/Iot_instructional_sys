<template>
  <div class="content-area">
    <div v-if="loading" class="content-area">
      <div class="skeleton card"></div>
      <div class="grid cards">
        <div v-for="i in 4" :key="i" class="skeleton card"></div>
      </div>
      <div class="skeleton card"></div>
    </div>
    <div v-else-if="error" class="msg-error" style="margin-bottom: 12px">{{ error }}</div>
    <template v-else>
      <section class="content-card profile-greeting">
        <div class="greeting-avatar">
          <img v-if="auth.user?.avatar_url" :src="auth.user.avatar_url" :alt="auth.user?.display_name || auth.user?.username" @error="onAvatarError" />
          <span :style="auth.user?.avatar_url ? 'display: none' : ''">{{ (auth.user?.display_name || auth.user?.username || '?').charAt(0).toUpperCase() }}</span>
        </div>
        <div class="greeting-text">
          <h2 class="greeting-title">{{ greeting }}，{{ auth.user?.display_name || auth.user?.username || '同学' }}！</h2>
          <p class="greeting-subtitle">欢迎来到智慧大棚学习平台，继续探索植物的奥秘吧</p>
        </div>
      </section>

      <section class="stat-grid">
        <div class="stat-card">
          <div class="stat-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
          </div>
          <div class="stat-value">{{ group?.name ?? '未分组' }}</div>
          <div class="stat-label">所属小组</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 9h6v6H9z"/></svg>
          </div>
          <div class="stat-value">{{ group?.node_id ? '在线' : '未绑定' }}</div>
          <div class="stat-label">设备状态</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
          </div>
          <div class="stat-value">{{ tasks.length }}</div>
          <div class="stat-label">待完成任务</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          </div>
          <div class="stat-value">{{ submissions.length }}</div>
          <div class="stat-label">已交作业</div>
        </div>
      </section>

      <section class="content-card">
        <div class="card-header">
          <h2 class="card-title">最新环境数据</h2>
          <span v-if="latestSensor" class="badge success"><span class="badge-dot"></span> 实时</span>
          <span v-else class="badge muted">暂无数据</span>
        </div>
        <div v-if="latestSensor" class="sensor-grid">
          <div class="sensor-item">
            <div class="sensor-label">气温</div>
            <div class="sensor-value">{{ latestSensor.air_temp?.toFixed(1) ?? '--' }}°C</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">空气湿度</div>
            <div class="sensor-value">{{ latestSensor.air_humidity?.toFixed(1) ?? '--' }}%</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">土壤湿度</div>
            <div class="sensor-value">{{ latestSensor.soil_humidity?.toFixed(1) ?? '--' }}%</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">光照强度</div>
            <div class="sensor-value">{{ latestSensor.light_intensity?.toFixed(0) ?? '--' }} lux</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">土壤pH</div>
            <div class="sensor-value">{{ latestSensor.soil_ph?.toFixed(1) ?? '--' }}</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">CO₂浓度</div>
            <div class="sensor-value">{{ latestSensor.co2?.toFixed(0) ?? '--' }} ppm</div>
          </div>
        </div>
        <EmptyState
          v-else
          icon="chart"
          title="本组设备暂无传感器数据"
          desc="设备上报后，这里会实时显示大棚环境"
        />
      </section>

      <section class="content-card">
        <div class="card-header">
          <h2 class="card-title">待办任务</h2>
          <RouterLink :to="{ name: 'student-tasks' }" class="btn ghost sm">查看全部</RouterLink>
        </div>
        <EmptyState
          v-if="pendingTasks.length === 0"
          icon="sprout"
          title="太棒了，任务都完成啦"
          desc="去环境数据看看，或者等老师布置新任务"
        />
        <div v-else class="task-list">
          <div v-for="task in pendingTasks.slice(0, 3)" :key="task.id" class="task-row">
            <div class="task-info">
              <div class="task-title">{{ task.title }}</div>
              <div class="task-meta">
                <span v-if="task.due_date" class="badge muted">截止 {{ task.due_date }}</span>
                <span v-if="task.task_type" class="badge info">{{ taskTypeLabel(task.task_type) }}</span>
              </div>
            </div>
            <RouterLink :to="{ name: 'student-tasks' }" class="btn primary sm">去完成</RouterLink>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import EmptyState from '@/components/EmptyState.vue'
import { taskTypeLabels } from '@/utils/labels'
import { fetchMyGroup, fetchMyTasks, fetchMySubmissions, fetchMyLatestSensorData } from '@/api/student'
import type { ClassTask, Group, SensorData, TaskSubmission, TaskType } from '@/types'

const auth = useAuthStore()
const loading = ref(true)
const group = ref<Group | null>(null)
const tasks = ref<ClassTask[]>([])
const submissions = ref<TaskSubmission[]>([])
const latestSensor = ref<SensorData | null>(null)
const error = ref('')

const pendingTasks = computed(() =>
  tasks.value.filter((t) => t.status === 'pending' || t.status === 'in_progress'),
)

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 11) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

function taskTypeLabel(type: TaskType | null): string {
  return type ? taskTypeLabels[type] : ''
}

function onAvatarError(event: Event) {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
  const sibling = img.nextElementSibling as HTMLElement | null
  if (sibling) {
    sibling.style.display = 'inline'
  }
}

async function loadData() {
  loading.value = true
  try {
    const [g, t, s, sensor] = await Promise.all([
      fetchMyGroup(),
      fetchMyTasks(),
      fetchMySubmissions(),
      fetchMyLatestSensorData(),
    ])
    group.value = g
    tasks.value = t
    submissions.value = s
    latestSensor.value = sensor
  } catch (err) {
    error.value = '数据加载失败，请确认后端已启动。'
    console.error('Failed to load student dashboard:', err)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>
