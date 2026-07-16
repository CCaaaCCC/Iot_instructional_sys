<template>
  <div class="grid" style="gap: 18px">
    <!-- Student list -->
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">学生列表</h3>
          <div class="card-subtitle">点击学生查看学习行为分析</div>
        </div>
        <div class="toolbar">
          <button class="btn secondary sm" @click="loadStudents">刷新</button>
        </div>
      </template>
      <table class="table" v-if="students.length">
        <thead>
          <tr>
            <th>姓名</th>
            <th>提交次数</th>
            <th>平均分</th>
            <th>已批阅</th>
            <th>完成率</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in students" :key="s.student_id" :class="{ 'selected-row': selectedId === s.student_id }">
            <td><strong>{{ s.student_name }}</strong></td>
            <td>{{ s.total_submissions }}</td>
            <td>{{ s.avg_score !== null ? s.avg_score + '分' : '-' }}</td>
            <td>{{ s.reviewed_count }}</td>
            <td>
              <span class="badge" :class="s.completion_rate >= 80 ? 'success' : s.completion_rate >= 50 ? 'warning' : 'danger'">
                {{ s.completion_rate }}%
              </span>
            </td>
            <td>
              <button class="btn secondary sm" @click="selectStudent(s.student_id)">
                查看详情
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="!loadingStudents" class="empty-state">
        <div class="empty-state-icon">👨‍🎓</div>
        暂无学生数据
      </div>
      <div v-else class="loading-state">加载中...</div>
    </SectionCard>

    <!-- Student detail -->
    <template v-if="selectedStudent">
      <SectionCard>
        <template #header>
          <div>
            <h3 class="card-title">{{ selectedStudent.summary.student_name }} - 学习画像</h3>
            <div class="card-subtitle">学习行为统计分析</div>
          </div>
          <div class="toolbar">
            <button class="btn primary sm" :disabled="exporting" @click="handleExportPdf">
              <span v-if="exporting">导出中...</span>
              <span v-else>导出成长档案 PDF</span>
            </button>
          </div>
        </template>
        <!-- Stat cards -->
        <div class="grid cards" style="margin-bottom:18px">
          <div class="stat-card blue">
            <div class="stat-icon">📝</div>
            <div class="stat-value">{{ selectedStudent.summary.total_submissions }}</div>
            <div class="stat-label">提交次数</div>
            <div class="stat-footnote">共完成 {{ selectedStudent.summary.completed_tasks }} / {{ selectedStudent.summary.total_tasks }} 个任务</div>
          </div>
          <div class="stat-card green">
            <div class="stat-icon">⭐</div>
            <div class="stat-value">{{ selectedStudent.summary.avg_score !== null ? selectedStudent.summary.avg_score + '分' : '-' }}</div>
            <div class="stat-label">平均得分</div>
          </div>
          <div class="stat-card gold">
            <div class="stat-icon">📊</div>
            <div class="stat-value">{{ selectedStudent.summary.completion_rate }}%</div>
            <div class="stat-label">任务完成率</div>
          </div>
          <div class="stat-card green">
            <div class="stat-icon">✅</div>
            <div class="stat-value">{{ selectedStudent.summary.on_time_ratio }}%</div>
            <div class="stat-label">按时提交率</div>
            <div class="stat-footnote">{{ selectedStudent.summary.on_time_count }} 按时 / {{ selectedStudent.summary.late_count }} 迟交</div>
          </div>
        </div>

        <!-- Trend chart -->
        <div v-if="echartsData && echartsData.x.length" style="margin-bottom:18px">
          <h4 style="margin-bottom:10px">📈 学习趋势</h4>
          <LineChart :data="echartsData" />
        </div>

        <!-- Recent activity -->
        <div>
          <h4 style="margin-bottom:10px">🕐 近期活动</h4>
          <div v-if="selectedStudent.recent_activity.length">
            <div v-for="(act, idx) in selectedStudent.recent_activity" :key="idx" style="display:flex;gap:12px;padding:8px 0;border-bottom:1px solid var(--line);align-items:flex-start">
              <span style="font-size:18px">{{ act.type === 'reviewed' ? '📋' : '✏️' }}</span>
              <div style="flex:1">
                <strong>{{ act.task_title || '未知任务' }}</strong>
                <div class="card-subtitle" style="font-size:13px">{{ act.date }} · {{ act.detail }}</div>
              </div>
              <span v-if="act.score !== null" class="badge success">{{ act.score }}分</span>
            </div>
          </div>
          <div v-else class="empty-state" style="padding:20px">
            <div class="empty-state-icon">📭</div>
            暂无活动记录
          </div>
        </div>
      </SectionCard>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import LineChart from '@/components/LineChart.vue'
import {
  fetchStudentsStats,
  fetchStudentAnalytics,
  fetchStudentECharts,
  exportStudentGrowthPdf,
} from '@/api/analytics'
import type {
  StudentStats,
  StudentAnalyticsFull,
  StudentEChartsResponse,
} from '@/types'

const students = ref<StudentStats[]>([])
const loadingStudents = ref(false)
const selectedId = ref<number | null>(null)
const selectedStudent = ref<StudentAnalyticsFull | null>(null)
const echartsData = ref<StudentEChartsResponse | null>(null)
const exporting = ref(false)

async function loadStudents() {
  loadingStudents.value = true
  try {
    students.value = await fetchStudentsStats({ limit: 100 })
  } finally {
    loadingStudents.value = false
  }
}

async function selectStudent(studentId: number) {
  selectedId.value = studentId
  try {
    const [analytics, echarts] = await Promise.all([
      fetchStudentAnalytics(studentId),
      fetchStudentECharts(studentId),
    ])
    selectedStudent.value = analytics
    echartsData.value = echarts
  } catch {
    selectedStudent.value = null
    echartsData.value = null
  }
}

async function handleExportPdf() {
  if (selectedId.value === null) return
  exporting.value = true
  try {
    const blob = await exportStudentGrowthPdf(selectedId.value)
    const studentName = selectedStudent.value?.summary.student_name ?? String(selectedId.value)
    const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    const filename = `学生成长档案_${studentName}_${dateStr}.pdf`
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('PDF 导出失败', err)
    alert('PDF 导出失败，请重试')
  } finally {
    exporting.value = false
  }
}

onMounted(loadStudents)
</script>
