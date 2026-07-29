<template>
  <div class="grid" style="gap: 18px">
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">创建实验</h3>
          <div class="card-subtitle">设计科学实验，指定变量指标和对照/实验组</div>
        </div>
      </template>
      <form class="form-grid" @submit.prevent="handleCreate">
        <label>
          <div class="form-label">实验标题 *</div>
          <input v-model="form.title" class="input" placeholder="请输入实验标题" required />
        </label>
        <label>
          <div class="form-label">所属班级 *</div>
          <select v-model="form.class_id" class="select" required>
            <option :value="0" disabled>请选择班级</option>
            <option v-for="c in classrooms" :key="c.id" :value="c.id">{{ c.name }}（{{ subjectLabel(c.subject) }}）</option>
          </select>
        </label>
        <label>
          <div class="form-label">变量指标 *</div>
          <select v-model="form.variable_metric" class="select" required>
            <option value="air_temp">空气温度</option>
            <option value="air_humidity">空气湿度</option>
            <option value="soil_humidity">土壤湿度</option>
            <option value="light_intensity">光照强度</option>
            <option value="soil_ph">土壤 pH</option>
            <option value="co2">CO₂浓度</option>
          </select>
        </label>
        <label>
          <div class="form-label">实验状态</div>
          <select v-model="form.status" class="select">
            <option value="ongoing">进行中</option>
            <option value="completed">已完成</option>
          </select>
        </label>
        <label>
          <div class="form-label">开始日期 *</div>
          <input v-model="form.start_date" class="input" type="date" required />
        </label>
        <label>
          <div class="form-label">结束日期 *</div>
          <input v-model="form.end_date" class="input" type="date" required />
        </label>
        <label class="form-grid-span">
          <div class="form-label">实验假设</div>
          <input v-model="form.hypothesis" class="input" placeholder="如：增加光照时长会提高植物生长速度" />
        </label>
        <label class="form-grid-span">
          <div class="form-label">结论（实验完成后填写）</div>
          <input v-model="form.conclusion" class="input" placeholder="可选，实验结论" />
        </label>
        <div style="display:flex;align-items:flex-end">
          <button class="btn primary">创建实验</button>
        </div>
      </form>
      <div v-if="message" class="msg-success">{{ message }}</div>
      <div v-if="error" class="msg-error">{{ error }}</div>
    </SectionCard>

    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">实验列表</h3>
          <div class="card-subtitle">管理所有科学实验，分配小组角色，查看观察记录</div>
        </div>
        <div class="toolbar">
          <select v-model="filterClassId" class="select" style="width: 160px" @change="loadExperiments">
            <option :value="undefined">全部班级</option>
            <option v-for="c in classrooms" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <button class="btn secondary sm" @click="loadExperiments">刷新</button>
        </div>
      </template>
      <table class="table">
        <thead>
          <tr>
            <th>标题</th>
            <th>班级</th>
            <th>变量指标</th>
            <th>状态</th>
            <th>日期</th>
            <th>假设</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="exp in experiments" :key="exp.id">
            <td><strong>{{ exp.title }}</strong></td>
            <td>{{ className(exp.class_id) }}</td>
            <td><span class="badge info"><span class="badge-dot"></span> {{ metricLabel(exp.variable_metric) }}</span></td>
            <td>
              <span class="badge" :class="exp.status === 'ongoing' ? 'warning' : 'success'">
                <span class="badge-dot"></span> {{ exp.status === 'ongoing' ? '进行中' : '已完成' }}
              </span>
            </td>
            <td>{{ exp.start_date }} ~ {{ exp.end_date }}</td>
            <td>{{ (exp.hypothesis || '').slice(0, 30) }}{{ (exp.hypothesis || '').length > 30 ? '...' : '' }}</td>
            <td>
              <button class="btn secondary sm" @click="openDetail(exp)">管理</button>
              <button class="btn danger sm" style="margin-left:4px" @click="handleDelete(exp)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!experiments.length" class="empty-state">
        暂无实验数据
      </div>
    </SectionCard>

    <Teleport to="body">
      <div v-if="detail.exp" class="modal-overlay" @click.self="closeDetail">
        <div class="modal-card" style="max-width: 800px; max-height: 90vh; overflow-y: auto">
          <div class="modal-header">
            <h3>实验管理：{{ detail.exp.title }}</h3>
            <button class="btn ghost sm" @click="closeDetail">关闭</button>
          </div>
          <div class="modal-body">
            <div v-if="detail.message" class="msg-success">{{ detail.message }}</div>

            <h4 style="margin-bottom: 8px">基本信息</h4>
            <div class="form-grid">
              <label>
                <div class="form-label">状态</div>
                <select v-model="detail.editStatus" class="select">
                  <option value="ongoing">进行中</option>
                  <option value="completed">已完成</option>
                </select>
              </label>
              <label>
                <div class="form-label">结论</div>
                <input v-model="detail.editConclusion" class="input" placeholder="实验结论" />
              </label>
              <label>
                <div class="form-label">开始日期</div>
                <input v-model="detail.editStartDate" class="input" type="date" />
              </label>
              <label>
                <div class="form-label">结束日期</div>
                <input v-model="detail.editEndDate" class="input" type="date" />
              </label>
            </div>
            <button class="btn primary sm" style="margin-top:8px" @click="saveDetail" :disabled="detail.saving">
              {{ detail.saving ? '保存中...' : '保存修改' }}
            </button>

            <div style="margin-top: 20px; border-top: 1px solid var(--line); padding-top: 16px">
              <h4 style="margin-bottom: 8px">参与小组</h4>
              <div class="form-grid">
                <label>
                  <div class="form-label">添加小组</div>
                  <select v-model="detail.newGroupId" class="select">
                    <option :value="0" disabled>选择小组</option>
                    <option v-for="g in availableGroups" :key="g.id" :value="g.id">{{ g.name }}</option>
                  </select>
                </label>
                <label>
                  <div class="form-label">角色</div>
                  <select v-model="detail.newGroupRole" class="select">
                    <option value="experimental">实验组</option>
                    <option value="control">对照组</option>
                  </select>
                </label>
                <label class="form-grid-span">
                  <div class="form-label">变量目标（可选）</div>
                  <input v-model="detail.newGroupTarget" class="input" placeholder="如：每天光照 12 小时" />
                </label>
              </div>
              <button class="btn primary sm" style="margin-top:8px" @click="addGroup" :disabled="!detail.newGroupId">添加小组</button>

              <table class="table" style="margin-top:12px">
                <thead>
                  <tr><th>小组</th><th>角色</th><th>变量目标</th><th>加入时间</th><th>操作</th></tr>
                </thead>
                <tbody>
                  <tr v-for="eg in detail.groups" :key="eg.id">
                    <td>{{ groupName(eg.group_id) }}</td>
                    <td>
                      <span class="badge" :class="eg.role === 'experimental' ? 'info' : 'warning'">
                        <span class="badge-dot"></span> {{ eg.role === 'experimental' ? '实验组' : '对照组' }}
                      </span>
                    </td>
                    <td>{{ eg.variable_target || '-' }}</td>
                    <td>{{ eg.created_at.slice(0, 10) }}</td>
                    <td>
                      <button class="btn danger sm" @click="removeGroup(eg.group_id)">移除</button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-if="!detail.groups.length" class="empty-state" style="padding:12px">暂无小组参与</div>
            </div>

            <div style="margin-top: 20px; border-top: 1px solid var(--line); padding-top: 16px">
              <h4 style="margin-bottom: 8px">学生观察记录</h4>
              <table class="table" v-if="detail.observations.length">
                <thead>
                  <tr><th>学生</th><th>内容</th><th>关联传感器数据</th><th>时间</th></tr>
                </thead>
                <tbody>
                  <tr v-for="obs in detail.observations" :key="obs.id">
                    <td>#{{ obs.student_id }}</td>
                    <td>{{ obs.content || '-' }}</td>
                    <td>{{ obs.sensor_data_id ? `#${obs.sensor_data_id}` : '-' }}</td>
                    <td>{{ obs.recorded_at.slice(0, 19).replace('T', ' ') }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="empty-state" style="padding:12px">暂无观察记录</div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import { createExperiment, deleteExperiment, fetchExperiments, updateExperiment, fetchExperimentGroups, addExperimentGroup, removeExperimentGroup, fetchObservations } from '@/api/experiments'
import { fetchClassrooms } from '@/api/classrooms'
import { fetchGroups } from '@/api/groups'
import type { Classroom, Experiment, ExperimentGroup, ExperimentObservation, ExperimentStatus, Group, SensorMetric } from '@/types'

const experiments = ref<Experiment[]>([])
const classrooms = ref<Classroom[]>([])
const groups = ref<Group[]>([])
const message = ref('')
const error = ref('')
const filterClassId = ref<number | undefined>(undefined)

const form = reactive({
  title: '',
  hypothesis: '',
  class_id: 0,
  variable_metric: 'air_temp' as SensorMetric,
  start_date: '',
  end_date: '',
  status: 'ongoing' as ExperimentStatus,
  conclusion: '',
})

const detail = reactive({
  exp: null as Experiment | null,
  editStatus: 'ongoing' as ExperimentStatus,
  editConclusion: '',
  editStartDate: '',
  editEndDate: '',
  groups: [] as ExperimentGroup[],
  observations: [] as ExperimentObservation[],
  message: '',
  saving: false,
  newGroupId: 0,
  newGroupRole: 'experimental' as string,
  newGroupTarget: '',
})

const metricLabels: Record<SensorMetric, string> = {
  air_temp: '空气温度',
  air_humidity: '空气湿度',
  soil_humidity: '土壤湿度',
  light_intensity: '光照强度',
  soil_ph: '土壤 pH',
  co2: 'CO₂浓度',
}
function metricLabel(m: SensorMetric) { return metricLabels[m] ?? m }

function subjectLabel(subject: string) {
  return subject === 'labor' ? '劳动课' : '科学课'
}

function className(classId: number) {
  return classrooms.value.find(c => c.id === classId)?.name ?? `#${classId}`
}

function groupName(groupId: number) {
  return groups.value.find(g => g.id === groupId)?.name ?? `#${groupId}`
}

const availableGroups = computed(() => {
  const assigned = new Set(detail.groups.map(g => g.group_id))
  return groups.value.filter(g => !assigned.has(g.id))
})

async function loadData() {
  try {
    const [c, g] = await Promise.all([fetchClassrooms(), fetchGroups()])
    classrooms.value = c
    groups.value = g
    await loadExperiments()
  } catch {
    error.value = '数据加载失败。'
  }
}

async function loadExperiments() {
  message.value = ''
  error.value = ''
  try {
    experiments.value = await fetchExperiments({ class_id: filterClassId.value })
  } catch {
    error.value = '实验列表加载失败。'
  }
}

async function handleCreate() {
  message.value = ''
  error.value = ''
  try {
    await createExperiment({
      title: form.title,
      hypothesis: form.hypothesis,
      class_id: form.class_id,
      variable_metric: form.variable_metric,
      start_date: form.start_date,
      end_date: form.end_date,
      status: form.status,
      conclusion: form.conclusion || null,
    })
    message.value = '实验创建成功'
    form.title = ''
    form.hypothesis = ''
    form.start_date = ''
    form.end_date = ''
    form.conclusion = ''
    await loadExperiments()
  } catch {
    error.value = '实验创建失败，请确认字段有效。'
  }
}

async function handleDelete(exp: Experiment) {
  if (!confirm(`确定删除实验「${exp.title}」吗？关联的小组和观察记录也将被删除。`)) return
  try {
    await deleteExperiment(exp.id)
    await loadExperiments()
  } catch {
    error.value = '删除失败。'
  }
}

async function openDetail(exp: Experiment) {
  detail.exp = exp
  detail.editStatus = exp.status
  detail.editConclusion = exp.conclusion ?? ''
  detail.editStartDate = exp.start_date
  detail.editEndDate = exp.end_date
  detail.message = ''
  detail.newGroupId = 0
  detail.newGroupTarget = ''
  try {
    const [eg, obs] = await Promise.all([
      fetchExperimentGroups(exp.id),
      fetchObservations(exp.id),
    ])
    detail.groups = eg
    detail.observations = obs
  } catch {
    detail.groups = []
    detail.observations = []
  }
}

function closeDetail() { detail.exp = null }

async function saveDetail() {
  if (!detail.exp) return
  detail.saving = true
  try {
    const updated = await updateExperiment(detail.exp.id, {
      status: detail.editStatus,
      conclusion: detail.editConclusion || null,
      start_date: detail.editStartDate,
      end_date: detail.editEndDate,
    })
    detail.exp = updated
    detail.message = '保存成功'
    await loadExperiments()
  } catch {
    detail.message = ''
  } finally {
    detail.saving = false
  }
}

async function addGroup() {
  if (!detail.exp || !detail.newGroupId) return
  try {
    await addExperimentGroup(detail.exp.id, {
      group_id: detail.newGroupId,
      role: detail.newGroupRole,
      variable_target: detail.newGroupTarget || null,
    })
    detail.newGroupId = 0
    detail.newGroupTarget = ''
    const eg = await fetchExperimentGroups(detail.exp.id)
    detail.groups = eg
    detail.message = '小组添加成功'
  } catch {
    detail.message = '添加失败'
  }
}

async function removeGroup(groupId: number) {
  if (!detail.exp) return
  try {
    await removeExperimentGroup(detail.exp.id, groupId)
    detail.groups = detail.groups.filter(g => g.group_id !== groupId)
    detail.message = '小组已移除'
  } catch {
    detail.message = '移除失败'
  }
}

onMounted(loadData)
</script>
