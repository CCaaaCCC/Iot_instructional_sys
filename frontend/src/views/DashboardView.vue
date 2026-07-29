<template>
  <div class="grid" style="gap: 18px">
    <div class="grid cards">
      <StatCard label="设备节点总数" :value="overview?.total_nodes ?? 0" footnote="已注册的 ESP32 设备节点" color="green" icon="devices" />
      <StatCard label="在线节点数" :value="overview?.online_nodes ?? 0" footnote="当前在线的设备节点" color="blue" icon="online" />
      <StatCard label="待办任务" :value="overview?.pending_tasks ?? 0" footnote="未完成的课堂任务" color="gold" icon="tasks" />
      <StatCard label="待批阅提交" :value="pendingReviewCount" footnote="学生已提交但未批阅" color="red" icon="rules" />
    </div>

    <div class="grid two-col">
      <SectionCard>
        <template #header>
          <div>
            <h3 class="card-title">班级概览</h3>
            <div class="card-subtitle">已创建的班级和所属小组进度</div>
          </div>
          <RouterLink v-if="canManageClassrooms" :to="{ name: 'classrooms' }" class="btn secondary sm">管理班级</RouterLink>
        </template>
        <div v-if="!classrooms.length" class="empty-state">
          暂无班级数据，请先创建班级
        </div>
        <div v-else class="grid" style="gap: 10px">
          <div v-for="c in classrooms" :key="c.id" class="classroom-card">
            <div class="classroom-header">
              <strong>{{ c.name }}</strong>
              <span class="badge" :class="c.subject === 'labor' ? 'warning' : 'info'">
                <span class="badge-dot"></span> {{ subjectLabel(c.subject) }}
              </span>
            </div>
            <div class="classroom-meta">
              <span class="badge success"><span class="badge-dot"></span> 小组数：{{ classroomGroupCount(c.id) }}</span>
              <span class="badge"><span class="badge-dot"></span> 班级 ID：{{ c.id }}</span>
            </div>
          </div>
        </div>
      </SectionCard>

      <SectionCard>
        <template #header>
          <div>
            <h3 class="card-title">最近任务</h3>
            <div class="card-subtitle">即将到期或进行中的课堂任务</div>
          </div>
          <RouterLink v-if="canManageTasks" :to="{ name: 'tasks' }" class="btn secondary sm">全部任务</RouterLink>
        </template>
        <div v-if="!tasks.length" class="empty-state">
          暂无任务
        </div>
        <table v-else class="table">
          <thead>
            <tr>
              <th>标题</th>
              <th>科目</th>
              <th>状态</th>
              <th>截止</th>
              <th>小组</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in tasks.slice(0, 5)" :key="task.id">
              <td><strong>{{ task.title }}</strong></td>
              <td>
                <span v-if="task.course_subject" class="badge" :class="task.course_subject === 'labor' ? 'warning' : 'info'">
                  <span class="badge-dot"></span> {{ subjectLabel(task.course_subject) }}
                </span>
                <span v-else>-</span>
              </td>
              <td><span class="badge" :class="taskStatusClass(task.status)"><span class="badge-dot"></span> {{ taskStatusLabel(task.status) }}</span></td>
              <td>{{ task.due_date || '-' }}</td>
              <td>{{ groupName(task.group_id) }}</td>
            </tr>
          </tbody>
        </table>
      </SectionCard>
    </div>

    <div class="grid two-col">
      <SectionCard>
        <template #header>
          <div>
            <h3 class="card-title">最新环境数据</h3>
            <div class="card-subtitle">最近一条传感器上报</div>
          </div>
        </template>
        <div v-if="overview?.latest_sensor_data" class="grid" style="gap: 10px">
          <div class="badge success"><span class="badge-dot"></span> 采样时间：{{ formatTime(overview.latest_sensor_data.recorded_at) }}</div>
          <div class="card-subtitle">节点 ID：{{ overview.latest_sensor_data.node_id }}</div>
          <table class="table">
            <tbody>
              <tr><th>空气温度</th><td>{{ displayValue(overview.latest_sensor_data.air_temp) }} ℃</td></tr>
              <tr><th>空气湿度</th><td>{{ displayValue(overview.latest_sensor_data.air_humidity) }} %</td></tr>
              <tr><th>土壤湿度</th><td>{{ displayValue(overview.latest_sensor_data.soil_humidity) }} %</td></tr>
              <tr><th>光照强度</th><td>{{ displayValue(overview.latest_sensor_data.light_intensity) }} lux</td></tr>
              <tr><th>土壤 pH</th><td>{{ displayValue(overview.latest_sensor_data.soil_ph) }}</td></tr>
              <tr><th>CO₂浓度</th><td>{{ displayValue(overview.latest_sensor_data.co2) }} ppm</td></tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-state">
          暂无传感器数据
        </div>
      </SectionCard>

      <SectionCard>
        <template #header>
          <div>
            <h3 class="card-title">待批阅提交</h3>
            <div class="card-subtitle">学生已提交但未批阅的作业</div>
          </div>
          <RouterLink v-if="canReview" :to="{ name: 'grading' }" class="btn primary sm">去批阅</RouterLink>
        </template>
        <div v-if="!pendingSubmissions.length" class="empty-state">
          暂无待批阅提交
        </div>
        <table v-else class="table">
          <thead>
            <tr>
              <th>提交 ID</th>
              <th>学生</th>
              <th>提交时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in pendingSubmissions.slice(0, 6)" :key="s.id">
              <td>#{{ s.id }}</td>
              <td>学生 #{{ s.student_id }}</td>
              <td>{{ formatTime(s.submitted_at) }}</td>
            </tr>
          </tbody>
        </table>
      </SectionCard>
    </div>

    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">组件状态汇总</h3>
          <div class="card-subtitle">按组件类型聚合（设备运维视图）</div>
        </div>
      </template>
      <table class="table">
        <thead>
          <tr>
            <th>类型</th>
            <th>总数</th>
            <th>开启</th>
            <th>关闭</th>
            <th>自动</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in componentSummary" :key="item.type">
            <td>{{ componentTypeLabel(item.type) }}</td>
            <td>{{ item.total }}</td>
            <td>{{ item.status_on }}</td>
            <td>{{ item.status_off }}</td>
            <td>{{ item.status_auto }}</td>
          </tr>
        </tbody>
      </table>
    </SectionCard>

    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">环境趋势</h3>
          <div class="card-subtitle">最近 24 条采样数据</div>
        </div>
        <span class="badge info"><span class="badge-dot"></span> ECharts</span>
      </template>
      <LineChart :data="chartData" />
    </SectionCard>

    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">系统状态</h3>
          <div class="card-subtitle">接口健康检查</div>
        </div>
        <div class="toolbar">
          <span v-if="connected" class="badge success"><span class="badge-dot"></span> 实时</span>
          <span v-else class="badge muted"><span class="badge-dot"></span> 离线</span>
        </div>
      </template>
      <div class="toolbar">
        <span class="badge success" v-if="loading"><span class="badge-dot"></span> 加载中</span>
        <span class="badge success" v-else><span class="badge-dot"></span> 已加载</span>
        <span v-if="error" class="badge danger"><span class="badge-dot"></span> {{ error }}</span>
        <span class="badge info">规则总数：{{ overview?.total_rules ?? 0 }}</span>
        <span class="badge warning">任务总数：{{ overview?.total_tasks ?? 0 }}</span>
      </div>
    </SectionCard>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import StatCard from '@/components/StatCard.vue'
import LineChart from '@/components/LineChart.vue'
import { fetchDashboardOverview, fetchComponentSummary } from '@/api/dashboard'
import { fetchSensorCharts } from '@/api/sensors'
import { fetchClassrooms } from '@/api/classrooms'
import { fetchGroups } from '@/api/groups'
import { fetchTasks } from '@/api/tasks'
import { fetchSubmissions } from '@/api/submissions'
import { useAuthStore } from '@/stores/auth'
import { useWebSocket } from '@/composables/useWebSocket'
import type {
  Classroom,
  ClassTask,
  ComponentSummaryItem,
  ComponentType,
  CourseSubject,
  DashboardOverview,
  EChartsResponse,
  Group,
  TaskSubmission,
} from '@/types'

const auth = useAuthStore()
const { connected, latestSensorData, componentUpdates, deviceStatuses } = useWebSocket()

const overview = ref<DashboardOverview | null>(null)
const componentSummary = ref<ComponentSummaryItem[]>([])
const chartData = ref<EChartsResponse | null>(null)
const classrooms = ref<Classroom[]>([])
const groups = ref<Group[]>([])
const tasks = ref<ClassTask[]>([])
const pendingSubmissions = ref<TaskSubmission[]>([])
const loading = ref(false)
const error = ref('')

const role = computed(() => auth.user?.role ?? '')
const canManageClassrooms = computed(() => role.value === 'admin' || role.value === 'teacher')
const canManageTasks = computed(() => role.value === 'admin' || role.value === 'teacher')
const canReview = computed(() => role.value === 'admin' || role.value === 'teacher')

const pendingReviewCount = computed(() => pendingSubmissions.value.length)

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN')
}

function displayValue(value: number | null) {
  return value === null || value === undefined ? '-' : value
}

function subjectLabel(subject: CourseSubject) {
  return subject === 'labor' ? '劳动课' : '科学课'
}

function componentTypeLabel(type: ComponentType) {
  const map: Record<ComponentType, string> = {
    fan: '风扇',
    pump: '水泵',
    light: '补光灯',
    sensor: '传感器',
  }
  return `${type} - ${map[type]}`
}

function taskStatusClass(status: string) {
  if (status === 'done') return 'success'
  if (status === 'in_progress') return 'warning'
  return ''
}

function taskStatusLabel(status: string) {
  if (status === 'done') return '已完成'
  if (status === 'in_progress') return '进行中'
  return '待开始'
}

function classroomGroupCount(classId: number) {
  return groups.value.filter((g) => g.class_id === classId).length
}

function groupName(groupId: number | null) {
  if (groupId === null) return '全体'
  return groups.value.find((g) => g.id === groupId)?.name ?? `#${groupId}`
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [overviewData, summaryData, chart] = await Promise.all([
      fetchDashboardOverview(),
      fetchComponentSummary(),
      fetchSensorCharts({ limit: 24 }),
    ])
    overview.value = overviewData
    componentSummary.value = summaryData
    chartData.value = chart

    if (canManageClassrooms.value) {
      const [classroomsData, groupsData, tasksData, pendingData] = await Promise.all([
        fetchClassrooms(),
        fetchGroups(),
        fetchTasks(),
        fetchSubmissions({ reviewed: false }),
      ])
      classrooms.value = classroomsData
      groups.value = groupsData
      tasks.value = tasksData
      pendingSubmissions.value = pendingData
    }
  } catch {
    error.value = '仪表盘数据加载失败，请确认后端已启动并完成初始化。'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

// WebSocket 实时更新：最新环境数据 + 环境趋势曲线
watch(latestSensorData, (data) => {
  if (!data) return
  // 更新"最新环境数据"卡片
  if (overview.value) {
    overview.value.latest_sensor_data = {
      id: data.id,
      node_id: data.node_id,
      air_temp: data.air_temp,
      air_humidity: data.air_humidity,
      soil_humidity: data.soil_humidity,
      light_intensity: data.light_intensity,
      soil_ph: data.soil_ph,
      co2: data.co2,
      recorded_at: data.recorded_at,
      created_at: data.recorded_at,
    }
  }
  // 追加到"环境趋势"曲线
  if (chartData.value) {
    const timestamp = new Date(data.recorded_at).toLocaleString('zh-CN')
    chartData.value.x.push(timestamp)
    chartData.value.x.shift()
    const metricMap: Record<string, number | null> = {
      'air_temp': data.air_temp,
      'air_humidity': data.air_humidity,
      'soil_humidity': data.soil_humidity,
      'light_intensity': data.light_intensity,
      'soil_ph': data.soil_ph,
      'co2': data.co2,
    }
    chartData.value.series.forEach((series) => {
      const value = metricMap[series.name]
      series.data.push(value ?? null)
      series.data.shift()
    })
  }
})

// WebSocket 实时更新：在线节点数
watch(deviceStatuses, (statuses) => {
  const latest = statuses[statuses.length - 1]
  if (!latest || !overview.value) return
  if (latest.online) {
    overview.value.online_nodes = (overview.value.online_nodes ?? 0) + 1
  } else {
    overview.value.online_nodes = Math.max(0, (overview.value.online_nodes ?? 0) - 1)
  }
})

// WebSocket 实时更新：组件状态汇总（重新加载）
watch(componentUpdates, async () => {
  try {
    componentSummary.value = await fetchComponentSummary()
  } catch {
    // 忽略：保持旧数据
  }
})
</script>

<style scoped>
.classroom-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 10px 12px;
  background: var(--panel);
}
.classroom-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.classroom-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
