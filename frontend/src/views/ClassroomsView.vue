<template>
  <div class="grid" style="gap: 18px">
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">新增班级</h3>
          <div class="card-subtitle">创建班级并选择所属科目（劳动课/科学课）</div>
        </div>
      </template>
      <form class="form-grid" @submit.prevent="handleCreate">
        <label>
          <div class="form-label">班级名称</div>
          <input v-model="form.name" class="input" placeholder="如：五(3)班" />
        </label>
        <label>
          <div class="form-label">科目</div>
          <select v-model="form.subject" class="select">
            <option value="labor">labor - 劳动课</option>
            <option value="science">science - 科学课</option>
          </select>
        </label>
        <div style="display:flex;align-items:flex-end">
          <button class="btn primary">创建班级</button>
        </div>
      </form>
      <div v-if="message" class="msg-success">{{ message }}</div>
      <div v-if="error" class="msg-error">{{ error }}</div>
    </SectionCard>

    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">班级列表</h3>
          <div class="card-subtitle">查看班级和小组数，点击展开查看小组</div>
        </div>
        <div class="toolbar">
          <select v-model="filterSubject" class="select" style="width: 160px">
            <option value="">全部科目</option>
            <option value="labor">劳动课</option>
            <option value="science">科学课</option>
          </select>
          <button class="btn secondary sm" @click="loadAll">刷新</button>
        </div>
      </template>

      <div v-if="!filteredClassrooms.length" class="empty-state">
        暂无班级，请先创建
      </div>

      <div v-else class="grid" style="gap: 14px">
        <div v-for="c in filteredClassrooms" :key="c.id" class="classroom-block">
          <div class="classroom-block-header">
            <div class="classroom-block-info">
              <strong>{{ c.name }}</strong>
              <span class="badge" :class="c.subject === 'labor' ? 'warning' : 'info'">
                <span class="badge-dot"></span> {{ subjectLabel(c.subject) }}
              </span>
              <span class="badge success"><span class="badge-dot"></span> 小组数：{{ classroomGroupCount(c.id) }}</span>
              <span class="classroom-meta-text">ID: {{ c.id }}</span>
            </div>
            <div class="classroom-block-actions">
              <button class="btn secondary sm" @click="toggleClassroom(c.id)">
                {{ expandedClassId === c.id ? '收起' : '展开' }}小组
              </button>
              <button class="btn danger sm" @click="handleDelete(c.id)">删除</button>
            </div>
          </div>

          <div v-if="expandedClassId === c.id" class="classroom-block-body">
            <div class="subgroup-add">
              <input v-model="newGroupName[c.id]" class="input" placeholder="新小组名称，如：第1组" style="width: 200px" />
              <button class="btn primary sm" @click="handleCreateGroup(c.id)">+ 添加小组</button>
            </div>
            <table class="table">
              <thead>
                <tr>
                  <th>小组名称</th>
                  <th>绑定节点</th>
                  <th>学生数</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="g in classroomGroups(c.id)" :key="g.id">
                  <td><strong>{{ g.name }}</strong></td>
                  <td>
                    <span v-if="g.node_id" class="badge success"><span class="badge-dot"></span> 节点 #{{ g.node_id }}</span>
                    <span v-else class="badge danger"><span class="badge-dot"></span> 未绑定</span>
                  </td>
                  <td>{{ groupStudentCount(g.id) }}</td>
                  <td>
                    <RouterLink :to="{ name: 'groups', query: { class_id: c.id } }" class="btn secondary sm">管理小组</RouterLink>
                  </td>
                </tr>
                <tr v-if="!classroomGroups(c.id).length">
                  <td colspan="4" class="empty-row">暂无小组，请在上方添加</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </SectionCard>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import { createClassroom, deleteClassroom, fetchClassrooms } from '@/api/classrooms'
import { createGroup, fetchGroups, fetchGroupStudents } from '@/api/groups'
import type { Classroom, CourseSubject, Group, User } from '@/types'

const classrooms = ref<Classroom[]>([])
const groups = ref<Group[]>([])
const studentsMap = ref<Record<number, User[]>>({})
const expandedClassId = ref<number | null>(null)
const newGroupName = reactive<Record<number, string>>({})
const message = ref('')
const error = ref('')
const filterSubject = ref<CourseSubject | ''>('')

const form = reactive({
  name: '',
  subject: 'labor' as CourseSubject,
})

const filteredClassrooms = computed(() => {
  if (!filterSubject.value) return classrooms.value
  return classrooms.value.filter((c) => c.subject === filterSubject.value)
})

function subjectLabel(subject: CourseSubject) {
  return subject === 'labor' ? '劳动课' : '科学课'
}

function classroomGroupCount(classId: number) {
  return groups.value.filter((g) => g.class_id === classId).length
}

function classroomGroups(classId: number) {
  return groups.value.filter((g) => g.class_id === classId)
}

function groupStudentCount(groupId: number) {
  return studentsMap.value[groupId]?.length ?? 0
}

async function loadAll() {
  message.value = ''
  error.value = ''
  try {
    const [classroomsData, groupsData] = await Promise.all([fetchClassrooms(), fetchGroups()])
    classrooms.value = classroomsData
    groups.value = groupsData
    studentsMap.value = {}
    await Promise.all(
      groupsData.map(async (g) => {
        try {
          studentsMap.value[g.id] = await fetchGroupStudents(g.id)
        } catch {
          studentsMap.value[g.id] = []
        }
      }),
    )
  } catch {
    error.value = '班级数据加载失败。'
  }
}

async function toggleClassroom(classId: number) {
  if (expandedClassId.value === classId) {
    expandedClassId.value = null
  } else {
    expandedClassId.value = classId
  }
}

async function handleCreate() {
  message.value = ''
  error.value = ''
  try {
    await createClassroom({ name: form.name, subject: form.subject })
    message.value = '班级创建成功'
    form.name = ''
    await loadAll()
  } catch {
    error.value = '班级创建失败，请确认名称唯一。'
  }
}

async function handleDelete(classId: number) {
  if (!confirm(`确认删除班级 #${classId}？此操作不影响已创建的小组，但小组将失去班级归属。`)) return
  try {
    await deleteClassroom(classId)
    message.value = '班级已删除'
    await loadAll()
  } catch {
    error.value = '班级删除失败。'
  }
}

async function handleCreateGroup(classId: number) {
  const name = newGroupName[classId]?.trim()
  if (!name) {
    error.value = '请输入小组名称'
    return
  }
  message.value = ''
  error.value = ''
  try {
    await createGroup({ name, class_id: classId })
    newGroupName[classId] = ''
    message.value = '小组创建成功'
    await loadAll()
  } catch {
    error.value = '小组创建失败。'
  }
}

onMounted(loadAll)
</script>

<style scoped>
.classroom-block {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 14px 16px;
  background: var(--panel);
}
.classroom-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.classroom-block-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.classroom-block-actions {
  display: flex;
  gap: 8px;
}
.classroom-meta-text {
  color: var(--muted);
  font-size: 13px;
}
.classroom-block-body {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed var(--line);
}
.subgroup-add {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  align-items: center;
}
.empty-row {
  text-align: center;
  color: var(--muted);
  padding: 16px;
}
</style>
