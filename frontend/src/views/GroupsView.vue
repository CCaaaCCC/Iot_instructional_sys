<template>
  <div class="grid" style="gap: 18px">
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">新增小组</h3>
          <div class="card-subtitle">为班级添加学习小组，每组可绑定一个设备节点</div>
        </div>
      </template>
      <form class="form-grid" @submit.prevent="handleCreateGroup">
        <label>
          <div class="form-label">所属班级</div>
          <select v-model="groupForm.class_id" class="select">
            <option :value="0" disabled>请选择班级</option>
            <option v-for="c in classrooms" :key="c.id" :value="c.id">{{ c.name }}（{{ subjectLabel(c.subject) }}）</option>
          </select>
        </label>
        <label>
          <div class="form-label">小组名称</div>
          <input v-model="groupForm.name" class="input" placeholder="如：第1组" />
        </label>
        <label>
          <div class="form-label">绑定节点（可选）</div>
          <select v-model="groupForm.node_id" class="select">
            <option :value="undefined">暂不绑定</option>
            <option v-for="n in availableNodes" :key="n.id" :value="n.id">节点 #{{ n.id }} {{ n.name }}</option>
          </select>
        </label>
        <div style="display:flex;align-items:flex-end">
          <button class="btn primary">创建小组</button>
        </div>
      </form>
      <div v-if="error" class="msg-error">{{ error }}</div>
    </SectionCard>

    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">小组概览</h3>
          <div class="card-subtitle">查看设备状态、任务进度、学生名单</div>
        </div>
        <div class="toolbar">
          <select v-model="filterClassId" class="select" style="width: 180px">
            <option :value="undefined">全部班级</option>
            <option v-for="c in classrooms" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <button class="btn secondary sm" @click="loadAll">刷新</button>
        </div>
      </template>

      <EmptyState
        v-if="!filteredGroups.length"
        icon="sprout"
        title="暂无小组"
        desc="在上方选择班级并填写小组名称，创建第一个小组"
      />

      <div v-else class="grid" style="gap: 14px">
        <div v-for="g in filteredGroups" :key="g.id" class="group-card">
          <div class="group-header">
            <div class="group-info">
              <strong>{{ g.name }}</strong>
              <span class="badge info"><span class="badge-dot"></span> {{ classroomLabel(g.class_id) }}</span>
              <span v-if="g.node_id" class="badge success"><span class="badge-dot"></span> 节点 #{{ g.node_id }} {{ nodeLabel(g.node_id) }}</span>
              <span v-else class="badge danger"><span class="badge-dot"></span> 未绑定节点</span>
              <span class="badge"><span class="badge-dot"></span> 学生 {{ groupStudentCount(g.id) }} 人</span>
            </div>
            <div class="group-actions">
              <button class="btn secondary sm" @click="toggleExpand(g.id)">
                {{ expandedGroupId === g.id ? '收起' : '展开' }}
              </button>
              <button class="btn danger sm" @click="handleDeleteGroup(g.id)">删除</button>
            </div>
          </div>

          <div v-if="expandedGroupId === g.id" class="group-body">
            <div class="group-section">
              <div class="group-section-title">设备节点绑定</div>
              <div class="node-bind-row">
                <select v-model="bindNodeSelect[g.id]" class="select" style="width: 280px">
                  <option :value="undefined">选择要绑定的节点</option>
                  <option v-for="n in allNodes" :key="n.id" :value="n.id">
                    节点 #{{ n.id }} {{ n.name }}{{ isNodeBoundByOther(g.id, n.id) ? '（已被其他组绑定）' : '' }}
                  </option>
                </select>
                <button class="btn primary sm" @click="handleBindNode(g.id)">绑定</button>
                <button v-if="g.node_id" class="btn secondary sm" @click="handleUnbindNode(g.id)">解绑</button>
              </div>
            </div>

            <div class="group-section">
              <div class="group-section-title">批量创建学生</div>
              <div class="batch-form">
                <label>
                  <div class="form-label">学生数量</div>
                  <input v-model.number="batchForms[g.id].count" class="input" type="number" min="1" max="20" style="width: 100px" />
                </label>
                <label style="flex: 1">
                  <div class="form-label">初始密码（至少 8 位，字母+数字）</div>
                  <input v-model="batchForms[g.id].password" class="input" type="text" placeholder="如：Student123" />
                </label>
                <button class="btn primary" @click="handleBatchCreate(g.id)">批量创建</button>
              </div>
              <div class="batch-hint">用户名将按 g{{ g.id }}s1、g{{ g.id }}s2... 规则自动生成</div>
            </div>

            <div class="group-section">
              <div class="group-section-title">学生名单</div>
              <table class="table">
                <thead>
                  <tr>
                    <th>用户名</th>
                    <th>显示名称</th>
                    <th>状态</th>
                    <th>创建时间</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="stu in groupStudents(g.id)" :key="stu.id">
                    <td><strong>{{ stu.username }}</strong></td>
                    <td>{{ stu.display_name || '-' }}</td>
                    <td><span class="badge" :class="stu.is_active ? 'success' : 'danger'"><span class="badge-dot"></span> {{ stu.is_active ? '启用' : '禁用' }}</span></td>
                    <td>{{ formatTime(stu.created_at) }}</td>
                  </tr>
                  <tr v-if="!groupStudents(g.id).length">
                    <td colspan="4" class="empty-row">暂无学生，请在上方批量创建</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </SectionCard>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import {
  batchCreateStudents,
  createGroup,
  deleteGroup,
  fetchGroupStudents,
  fetchGroups,
  bindNode,
  unbindNode,
} from '@/api/groups'
import { fetchClassrooms } from '@/api/classrooms'
import { fetchNodes } from '@/api/device_nodes'
import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import type { Classroom, CourseSubject, DeviceNode, Group, User } from '@/types'

const classrooms = ref<Classroom[]>([])
const groups = ref<Group[]>([])
const allNodes = ref<DeviceNode[]>([])
const studentsMap = ref<Record<number, User[]>>({})
const expandedGroupId = ref<number | null>(null)
const bindNodeSelect = reactive<Record<number, number | undefined>>({})
const batchForms = reactive<Record<number, { count: number; password: string }>>({})
const error = ref('')
const confirm = useConfirm()
const toast = useToast()
const filterClassId = ref<number | undefined>(undefined)

const groupForm = reactive({
  name: '',
  class_id: 0,
  node_id: undefined as number | undefined,
})

const filteredGroups = computed(() => {
  if (filterClassId.value === undefined) return groups.value
  return groups.value.filter((g) => g.class_id === filterClassId.value)
})

const availableNodes = computed(() => allNodes.value)

function subjectLabel(subject: CourseSubject) {
  return subject === 'labor' ? '劳动课' : '科学课'
}

function classroomLabel(classId: number) {
  return classrooms.value.find((c) => c.id === classId)?.name ?? `#${classId}`
}

function nodeLabel(nodeId: number) {
  return allNodes.value.find((n) => n.id === nodeId)?.name ?? ''
}

function groupStudentCount(groupId: number) {
  return studentsMap.value[groupId]?.length ?? 0
}

function groupStudents(groupId: number) {
  return studentsMap.value[groupId] ?? []
}

function isNodeBoundByOther(currentGroupId: number, nodeId: number) {
  return groups.value.some((g) => g.id !== currentGroupId && g.node_id === nodeId)
}

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN')
}

function ensureBatchForm(groupId: number) {
  if (!batchForms[groupId]) {
    batchForms[groupId] = { count: 4, password: 'Student123' }
  }
}

async function loadAll() {
  error.value = ''
  try {
    const [classroomsData, groupsData, nodesData] = await Promise.all([
      fetchClassrooms(),
      fetchGroups(),
      fetchNodes(),
    ])
    classrooms.value = classroomsData
    groups.value = groupsData
    allNodes.value = nodesData
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
    error.value = '小组数据加载失败。'
  }
}

function toggleExpand(groupId: number) {
  if (expandedGroupId.value === groupId) {
    expandedGroupId.value = null
    return
  }
  expandedGroupId.value = groupId
  ensureBatchForm(groupId)
  if (!bindNodeSelect[groupId]) bindNodeSelect[groupId] = undefined
}

async function handleCreateGroup() {
  if (!groupForm.class_id) {
    toast.warning('请先选择所属班级')
    return
  }
  if (!groupForm.name.trim()) {
    toast.warning('请输入小组名称')
    return
  }
  try {
    const payload: { name: string; class_id: number; node_id?: number } = {
      name: groupForm.name.trim(),
      class_id: groupForm.class_id,
    }
    if (groupForm.node_id !== undefined) payload.node_id = groupForm.node_id
    await createGroup(payload)
    toast.success('小组已创建')
    groupForm.name = ''
    groupForm.node_id = undefined
    await loadAll()
  } catch {
    toast.error('小组创建失败，请检查填写内容')
  }
}

async function handleDeleteGroup(groupId: number) {
  const ok = await confirm({
    title: '删除小组',
    message: `删除小组 #${groupId} 后，该组的学生账号关联也将一并移除。`,
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  try {
    await deleteGroup(groupId)
    toast.success('小组已删除')
    if (expandedGroupId.value === groupId) expandedGroupId.value = null
    await loadAll()
  } catch {
    toast.error('小组删除失败，请稍后重试')
  }
}

async function handleBindNode(groupId: number) {
  const nodeId = bindNodeSelect[groupId]
  if (!nodeId) {
    toast.warning('请先选择要绑定的设备节点')
    return
  }
  try {
    await bindNode(groupId, nodeId)
    toast.success(`节点 #${nodeId} 已绑定到小组 #${groupId}`)
    bindNodeSelect[groupId] = undefined
    await loadAll()
  } catch {
    toast.error('绑定失败，该节点可能已被其他小组占用')
  }
}

async function handleUnbindNode(groupId: number) {
  try {
    await unbindNode(groupId)
    toast.success(`小组 #${groupId} 已解绑节点`)
    await loadAll()
  } catch {
    toast.error('解绑失败，请稍后重试')
  }
}

async function handleBatchCreate(groupId: number) {
  const form = batchForms[groupId]
  if (!form) return
  if (!form.count || form.count < 1 || form.count > 20) {
    toast.warning('学生数量应在 1-20 之间')
    return
  }
  if (form.password.length < 8) {
    toast.warning('密码至少需要 8 位')
    return
  }
  if (!/[a-zA-Z]/.test(form.password) || !/\d/.test(form.password)) {
    toast.warning('密码需同时包含字母和数字')
    return
  }
  try {
    const created = await batchCreateStudents(groupId, {
      group_id: groupId,
      count: form.count,
      password: form.password,
    })
    toast.success(`已创建 ${created.length} 个学生账号`)
    studentsMap.value[groupId] = await fetchGroupStudents(groupId)
  } catch {
    toast.error('批量创建失败，请检查密码复杂度')
  }
}

onMounted(async () => {
  await loadAll()
  // 优先展开 query.class_id 对应的小组
  const urlParams = new URLSearchParams(window.location.search)
  const queryClassId = urlParams.get('class_id')
  if (queryClassId) {
    filterClassId.value = Number(queryClassId)
  }
})
</script>

<style scoped>
.group-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 14px 16px;
  background: var(--panel);
}
.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.group-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.group-actions {
  display: flex;
  gap: 8px;
}
.group-body {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed var(--line);
  display: grid;
  gap: 16px;
}
.group-section {
  background: var(--panel);
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid var(--line);
}
.group-section-title {
  font-weight: 600;
  margin-bottom: 8px;
  font-size: 14px;
}
.node-bind-row {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.batch-form {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  flex-wrap: wrap;
}
.batch-hint {
  margin-top: 6px;
  font-size: 13px;
  color: var(--muted);
}
.empty-row {
  text-align: center;
  color: var(--muted);
  padding: 16px;
}
</style>
