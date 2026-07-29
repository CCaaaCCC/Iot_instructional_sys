<template>
  <div class="grid" style="gap: 18px">
    <!-- 班级选择器 -->
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">班级驾驶舱</h3>
          <div class="card-subtitle">教师一眼看清班级整体学情、小组表现和任务完成情况</div>
        </div>
        <div class="toolbar">
          <select v-model="selectedClassroomId" class="select" @change="loadOverview">
            <option v-for="c in classrooms" :key="c.id" :value="c.id">{{ c.name }}（{{ subjectLabel(c.subject) }}）</option>
          </select>
          <button class="btn secondary sm" @click="loadOverview">刷新</button>
        </div>
      </template>

      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="!overview" class="empty-state">
        请选择班级查看驾驶舱数据
      </div>
      <template v-else>
        <!-- KPI 卡片 -->
        <div class="grid cards" style="margin-bottom: 18px">
          <div class="stat-card blue">
            <div class="stat-value">{{ overview.total_students }}</div>
            <div class="stat-label">班级人数</div>
            <div class="stat-footnote">{{ overview.total_groups }} 个小组 · {{ overview.total_tasks }} 个任务</div>
          </div>
          <div class="stat-card gold">
            <div class="stat-value">{{ overview.avg_completion_rate }}%</div>
            <div class="stat-label">平均完成率</div>
            <div class="stat-footnote">按时提交率 {{ overview.on_time_ratio }}%</div>
          </div>
          <div class="stat-card green">
            <div class="stat-value">{{ overview.avg_score !== null ? overview.avg_score + '分' : '-' }}</div>
            <div class="stat-label">平均得分</div>
            <div class="stat-footnote">班级所有已批阅作业</div>
          </div>
          <div class="stat-card red">
            <div class="stat-value">{{ overview.pending_review_count }}</div>
            <div class="stat-label">待批阅</div>
            <div class="stat-footnote">学生已提交未批阅</div>
          </div>
        </div>

        <!-- 图表区域 -->
        <div class="grid two-col" style="margin-bottom: 18px">
          <div>
            <h4 style="margin-bottom: 10px">各小组完成率</h4>
            <div ref="groupChartRef" class="chart-box"></div>
          </div>
          <div>
            <h4 style="margin-bottom: 10px">评分分布</h4>
            <div ref="scoreChartRef" class="chart-box"></div>
          </div>
        </div>

        <!-- 小组排行榜 -->
        <div style="margin-bottom: 18px">
          <h4 style="margin-bottom: 10px">小组表现排行</h4>
          <table class="table" v-if="overview.groups.length">
            <thead>
              <tr>
                <th>排名</th>
                <th>小组</th>
                <th>人数</th>
                <th>提交数</th>
                <th>平均分</th>
                <th>完成率</th>
                <th>待批阅</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(g, idx) in sortedGroups" :key="g.group_id">
                <td>
                  <span class="badge" :class="idx === 0 ? 'success' : idx === 1 ? 'info' : idx === 2 ? 'warning' : ''">
                    <span class="badge-dot"></span> 第 {{ idx + 1 }} 名
                  </span>
                </td>
                <td><strong>{{ g.group_name }}</strong></td>
                <td>{{ g.student_count }}</td>
                <td>{{ g.submission_count }}</td>
                <td>{{ g.avg_score !== null ? g.avg_score + '分' : '-' }}</td>
                <td>
                  <div class="progress-bar">
                    <div class="progress-fill" :class="g.completion_rate >= 80 ? 'success' : g.completion_rate >= 50 ? 'warning' : 'danger'" :style="{ width: g.completion_rate + '%' }"></div>
                    <span class="progress-text">{{ g.completion_rate }}%</span>
                  </div>
                </td>
                <td>
                  <span v-if="g.pending_review_count > 0" class="badge danger"><span class="badge-dot"></span> {{ g.pending_review_count }}</span>
                  <span v-else class="card-subtitle">-</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-state">暂无小组数据</div>
        </div>

        <!-- 任务完成情况 -->
        <div>
          <h4 style="margin-bottom: 10px">任务完成情况</h4>
          <table class="table" v-if="overview.tasks.length">
            <thead>
              <tr>
                <th>任务标题</th>
                <th>类型</th>
                <th>状态</th>
                <th>截止日期</th>
                <th>已提交</th>
                <th>未交人数</th>
                <th>平均分</th>
                <th>完成进度</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in overview.tasks" :key="t.task_id">
                <td><strong>{{ t.task_title }}</strong></td>
                <td>
                  <span v-if="t.task_type" class="badge info"><span class="badge-dot"></span> {{ taskTypeLabel(t.task_type) }}</span>
                  <span v-else class="card-subtitle">-</span>
                </td>
                <td>
                  <span class="badge" :class="statusClass(t.status)"><span class="badge-dot"></span> {{ statusLabel(t.status) }}</span>
                </td>
                <td>{{ t.due_date || '-' }}</td>
                <td>{{ t.total_submissions }}</td>
                <td>
                  <span v-if="t.unsubmitted_count > 0" class="badge warning"><span class="badge-dot"></span> {{ t.unsubmitted_count }} 人</span>
                  <span v-else class="badge success"><span class="badge-dot"></span> 全部已交</span>
                </td>
                <td>{{ t.avg_score !== null ? t.avg_score + '分' : '-' }}</td>
                <td>
                  <div class="progress-bar">
                    <div class="progress-fill" :class="taskProgressRate(t) >= 80 ? 'success' : taskProgressRate(t) >= 50 ? 'warning' : 'danger'" :style="{ width: taskProgressRate(t) + '%' }"></div>
                    <span class="progress-text">{{ taskProgressRate(t) }}%</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-state">暂无任务数据</div>
        </div>
      </template>
    </SectionCard>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import SectionCard from '@/components/SectionCard.vue'
import { fetchClassrooms } from '@/api/classrooms'
import { fetchClassroomOverview } from '@/api/analytics'
import { useTheme } from '@/composables/useTheme'
import type { Classroom, ClassroomOverview, CourseSubject } from '@/types'

const { theme } = useTheme()

const classrooms = ref<Classroom[]>([])
const selectedClassroomId = ref<number | null>(null)
const overview = ref<ClassroomOverview | null>(null)
const loading = ref(false)

const groupChartRef = ref<HTMLDivElement | null>(null)
const scoreChartRef = ref<HTMLDivElement | null>(null)
let groupChart: echarts.ECharts | null = null
let scoreChart: echarts.ECharts | null = null

const sortedGroups = computed(() => {
  if (!overview.value) return []
  return [...overview.value.groups].sort((a, b) => b.completion_rate - a.completion_rate)
})

function subjectLabel(s: CourseSubject | null | undefined): string {
  if (s === 'labor') return '劳动课'
  if (s === 'science') return '科学课'
  return '-'
}

function taskTypeLabel(t: string): string {
  const map: Record<string, string> = { observation: '观察', experiment: '实验', maintenance: '维护' }
  return map[t] || t
}

function statusLabel(s: string): string {
  const map: Record<string, string> = { pending: '待开始', in_progress: '进行中', done: '已完成' }
  return map[s] || s
}

function statusClass(s: string): string {
  const map: Record<string, string> = { pending: '', in_progress: 'warning', done: 'success' }
  return map[s] || ''
}

function taskProgressRate(t: { total_submissions: number; unsubmitted_count: number }): number {
  const total = t.total_submissions + t.unsubmitted_count
  if (total === 0) return 0
  return Math.round((t.total_submissions / total) * 100)
}

async function loadClassrooms() {
  try {
    classrooms.value = await fetchClassrooms()
    if (classrooms.value.length && selectedClassroomId.value === null) {
      selectedClassroomId.value = classrooms.value[0].id
      await loadOverview()
    }
  } catch (e) {
    console.error('Failed to load classrooms', e)
  }
}

async function loadOverview() {
  if (selectedClassroomId.value === null) return
  loading.value = true
  overview.value = null
  try {
    overview.value = await fetchClassroomOverview(selectedClassroomId.value)
    await nextTick()
    renderCharts()
  } catch (e) {
    console.error('Failed to load classroom overview', e)
  } finally {
    loading.value = false
  }
}

function getChartColors() {
  return theme.value === 'light'
    ? ['#16a34a', '#d97706', '#2563eb', '#dc2626', '#7c3aed', '#0891b2']
    : ['#b8d68a', '#f0b878', '#e08868', '#e88080', '#8ab8d8', '#c9a8d8']
}

function getBaseOptions() {
  const isLight = theme.value === 'light'
  return {
    tooltip: {
      backgroundColor: isLight ? 'rgba(255, 255, 255, 0.96)' : 'rgba(20, 16, 11, 0.92)',
      borderColor: isLight ? 'rgba(0, 0, 0, 0.08)' : 'rgba(240, 184, 120, 0.18)',
      borderWidth: 1,
      textStyle: { color: isLight ? '#1a1a2e' : '#f4ecd8', fontSize: 12 },
    },
    xAxis: {
      axisLabel: { color: isLight ? '#6b7280' : '#9a8a6a', fontSize: 11 },
      axisLine: { lineStyle: { color: isLight ? 'rgba(0, 0, 0, 0.08)' : 'rgba(240, 184, 120, 0.14)' } },
      axisTick: { show: false },
    },
    yAxis: {
      axisLabel: { color: isLight ? '#6b7280' : '#9a8a6a', fontSize: 11 },
      splitLine: { lineStyle: { color: isLight ? 'rgba(0, 0, 0, 0.06)' : 'rgba(255, 220, 160, 0.05)' } },
      axisLine: { show: false },
      axisTick: { show: false },
    },
  }
}

function renderCharts() {
  if (!overview.value) return
  const palette = getChartColors()
  const base = getBaseOptions()

  // 小组完成率柱状图
  if (groupChartRef.value && !groupChart) {
    groupChart = echarts.init(groupChartRef.value)
  }
  if (groupChart) {
    const gc = overview.value.echarts.group_completion
    groupChart.setOption({
      backgroundColor: 'transparent',
      ...base,
      grid: { left: 44, right: 20, top: 30, bottom: 28 },
      xAxis: { ...base.xAxis, type: 'category', data: gc.x },
      yAxis: { ...base.yAxis, type: 'value', max: 100, axisLabel: { ...base.yAxis.axisLabel, formatter: '{value}%' } },
      series: [{
        type: 'bar',
        data: gc.series[0]?.data ?? [],
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: palette[0] },
            { offset: 1, color: palette[1] },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
        barWidth: '50%',
      }],
    }, true)
  }

  // 评分分布柱状图
  if (scoreChartRef.value && !scoreChart) {
    scoreChart = echarts.init(scoreChartRef.value)
  }
  if (scoreChart) {
    const sd = overview.value.echarts.score_distribution
    scoreChart.setOption({
      backgroundColor: 'transparent',
      ...base,
      grid: { left: 44, right: 20, top: 30, bottom: 28 },
      xAxis: { ...base.xAxis, type: 'category', data: sd.x },
      yAxis: { ...base.yAxis, type: 'value' },
      series: [{
        type: 'bar',
        data: sd.series[0]?.data ?? [],
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: palette[3] },
            { offset: 1, color: palette[2] },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
        barWidth: '50%',
      }],
    }, true)
  }
}

function resizeCharts() {
  groupChart?.resize()
  scoreChart?.resize()
}

watch(theme, () => renderCharts())

onMounted(async () => {
  await loadClassrooms()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  groupChart?.dispose()
  scoreChart?.dispose()
  groupChart = null
  scoreChart = null
})
</script>

<style scoped>
.chart-box {
  width: 100%;
  min-height: 280px;
}

.progress-bar {
  position: relative;
  width: 100%;
  height: 18px;
  background: var(--panel-hover);
  border-radius: 9px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 9px;
  transition: width 0.3s ease;
}

.progress-fill.success {
  background: linear-gradient(90deg, #16a34a, #4ade80);
}

.progress-fill.warning {
  background: linear-gradient(90deg, #d97706, #fbbf24);
}

.progress-fill.danger {
  background: linear-gradient(90deg, #dc2626, #f87171);
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 11px;
  font-weight: 600;
  color: var(--text);
  text-shadow: 0 0 4px rgba(255, 255, 255, 0.5);
}

.toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
}

.input {
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--input-bg);
  color: var(--text);
  font-size: 13px;
  min-width: 180px;
}
</style>
