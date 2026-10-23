<template>
  <div class="grid" style="gap: 18px">
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">新增课堂任务</h3>
          <div class="card-subtitle">用于劳动课/科学课教学安排，可指定给小组</div>
        </div>
      </template>
      <form class="form-grid" @submit.prevent="handleCreate">
        <label>
          <div class="form-label">任务标题</div>
          <input v-model="form.title" class="input" placeholder="请输入任务标题" />
        </label>
        <label>
          <div class="form-label">所属班级</div>
          <select v-model="form.group_id" class="select">
            <option :value="null">不指定小组（全体任务）</option>
            <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}（#{{ g.id }}）</option>
          </select>
        </label>
        <label>
          <div class="form-label">课程科目</div>
          <select v-model="form.course_subject" class="select">
            <option value="labor">劳动课</option>
            <option value="science">科学课</option>
          </select>
        </label>
        <label>
          <div class="form-label">任务类型</div>
          <select v-model="form.task_type" class="select">
            <option value="observation">观察记录</option>
            <option value="experiment">实验操作</option>
            <option value="maintenance">日常维护</option>
          </select>
        </label>
        <label>
          <div class="form-label">任务状态</div>
          <select v-model="form.status" class="select">
            <option value="pending">待开始</option>
            <option value="in_progress">进行中</option>
            <option value="done">已完成</option>
          </select>
        </label>
        <label>
          <div class="form-label">开始日期</div>
          <input v-model="form.assigned_date" class="input" type="date" />
        </label>
        <label>
          <div class="form-label">截止日期</div>
          <input v-model="form.due_date" class="input" type="date" />
        </label>
        <label>
          <div class="form-label">描述</div>
          <input v-model="form.description" class="input" placeholder="可选，任务描述" />
        </label>
        <div style="display:flex;align-items:flex-end">
          <button class="btn primary">创建任务</button>
        </div>
      </form>

    </SectionCard>

    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">任务列表</h3>
          <div class="card-subtitle">跟踪课堂任务完成情况，支持按小组筛选</div>
        </div>
        <div class="toolbar">
          <select v-model="filterGroupId" class="select" style="width: 180px" @change="loadTasks">
            <option :value="undefined">全部小组</option>
            <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
          <button class="btn secondary sm" @click="loadTasks">刷新</button>
        </div>
      </template>
      <table class="table">
        <thead>
          <tr>
            <th>标题</th>
            <th>科目</th>
            <th>类型</th>
            <th>状态</th>
            <th>小组</th>
            <th>开始</th>
            <th>截止</th>
            <th>描述</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in tasks" :key="task.id">
            <td><strong>{{ task.title }}</strong></td>
            <td>
              <span v-if="task.course_subject" class="badge" :class="task.course_subject === 'labor' ? 'warning' : 'info'">
                <span class="badge-dot"></span> {{ subjectLabel(task.course_subject) }}
              </span>
              <span v-else>-</span>
            </td>
            <td>{{ task.task_type ? taskTypeLabel(task.task_type) : '-' }}</td>
            <td><span class="badge" :class="taskStatusClass(task.status)"><span class="badge-dot"></span> {{ taskStatusLabel(task.status) }}</span></td>
            <td>{{ groupName(task.group_id) }}</td>
            <td>{{ task.assigned_date || '-' }}</td>
            <td>{{ task.due_date || '-' }}</td>
            <td>{{ task.description || '-' }}</td>
          </tr>
        </tbody>
      </table>
      <EmptyState
        v-if="!tasks.length"
        icon="inbox"
        title="暂无课堂任务"
        desc="在上方填写任务标题，为小组布置第一项任务"
      />
    </SectionCard>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useToast } from '@/composables/useToast'
import { createTask, fetchTasks } from '@/api/tasks'
import { fetchGroups } from '@/api/groups'
import { taskTypeLabels } from '@/utils/labels'
import type { ClassTask, CourseSubject, Group, TaskStatus, TaskType } from '@/types'

const tasks = ref<ClassTask[]>([])
const groups = ref<Group[]>([])
const error = ref('')
const toast = useToast()
const filterGroupId = ref<number | undefined>(undefined)

const form = reactive({
  title: '',
  description: '',
  assigned_date: '',
  due_date: '',
  status: 'pending' as TaskStatus,
  group_id: null as number | null,
  course_subject: 'labor' as CourseSubject,
  task_type: 'observation' as TaskType,
})

function taskStatusClass(status: TaskStatus) {
  if (status === 'done') return 'success'
  if (status === 'in_progress') return 'warning'
  return ''
}

function taskStatusLabel(status: TaskStatus) {
  if (status === 'done') return '已完成'
  if (status === 'in_progress') return '进行中'
  return '待开始'
}

function subjectLabel(subject: CourseSubject) {
  return subject === 'labor' ? '劳动课' : '科学课'
}

function taskTypeLabel(type: TaskType) {
  return taskTypeLabels[type] ?? '—'
}

function groupName(groupId: number | null) {
  if (groupId === null) return '全体'
  return groups.value.find((g) => g.id === groupId)?.name ?? `#${groupId}`
}

async function loadGroups() {
  try {
    groups.value = await fetchGroups()
  } catch {
    toast.error('小组列表加载失败')
  }
}

async function loadTasks() {
  try {
    tasks.value = await fetchTasks({ group_id: filterGroupId.value })
  } catch {
    toast.error('任务列表加载失败')
  }
}

async function handleCreate() {
  if (!form.title.trim()) {
    toast.warning('请填写任务标题')
    return
  }
  if (form.assigned_date && form.due_date && form.due_date < form.assigned_date) {
    toast.warning('截止日期不能早于开始日期')
    return
  }
  try {
    await createTask({
      title: form.title,
      description: form.description || null,
      assigned_date: form.assigned_date || null,
      due_date: form.due_date || null,
      status: form.status,
      group_id: form.group_id,
      course_subject: form.course_subject,
      task_type: form.task_type,
    })
    toast.success('课堂任务已创建')
    form.title = ''
    form.description = ''
    form.assigned_date = ''
    form.due_date = ''
    form.status = 'pending'
    form.group_id = null
    await loadTasks()
  } catch {
    toast.error('任务创建失败，请检查填写内容')
  }
}

onMounted(async () => {
  await loadGroups()
  await loadTasks()
})
</script>
