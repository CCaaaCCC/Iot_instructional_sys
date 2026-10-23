<template>
  <div class="content-area">
    <div v-if="loading" class="content-area">
      <div v-for="i in 3" :key="i" class="skeleton card"></div>
    </div>
    <div v-else-if="error" class="msg-error" style="margin-bottom: 12px">{{ error }}</div>
    <template v-else>
      <EmptyState
        v-if="experiments.length === 0"
        icon="flask"
        title="老师还没有创建实验项目"
        desc="实验开始后，你可以在这里记录观察数据"
      />
      <div v-else class="task-list-vertical">
        <article v-for="exp in experiments" :key="exp.id" class="content-card task-card">
          <div class="task-card-header">
            <h2 class="card-title">{{ exp.title }}</h2>
            <div class="task-badges">
              <span class="badge" :class="exp.status === 'ongoing' ? 'warning' : 'success'">
                <span class="badge-dot"></span> {{ exp.status === 'ongoing' ? '进行中' : '已完成' }}
              </span>
              <span v-if="expGroupMap[exp.id]" class="badge" :class="expGroupMap[exp.id].role === 'experimental' ? 'info' : 'warning'">
                <span class="badge-dot"></span> {{ expGroupMap[exp.id].role === 'experimental' ? '实验组' : '对照组' }}
              </span>
              <span class="badge muted">{{ metricLabel(exp.variable_metric) }}</span>
            </div>
          </div>

          <p v-if="exp.hypothesis" class="task-description">
            <strong>假设：</strong>{{ exp.hypothesis }}
          </p>

          <div class="task-meta-row">
            <span class="meta-item">日期：{{ exp.start_date }} ~ {{ exp.end_date }}</span>
            <span v-if="exp.conclusion" class="meta-item"><strong>结论：</strong>{{ exp.conclusion }}</span>
          </div>

          <div class="task-card-footer">
            <button class="btn primary sm" @click="openDetail(exp)">查看详情 & 记录观察</button>
          </div>
        </article>
      </div>

      <Teleport to="body">
        <div v-if="detail.exp" class="modal-overlay" @click.self="closeDetail">
          <div class="modal-card" style="max-width: 800px; max-height: 90vh; overflow-y: auto">
            <div class="modal-header">
              <h3>{{ detail.exp.title }}</h3>
              <button class="btn ghost sm" @click="closeDetail">关闭</button>
            </div>
            <div class="modal-body">
              <div class="form-grid">
                <div>
                  <div class="form-label">实验状态</div>
                  <span class="badge" :class="detail.exp.status === 'ongoing' ? 'warning' : 'success'">
                    <span class="badge-dot"></span> {{ detail.exp.status === 'ongoing' ? '进行中' : '已完成' }}
                  </span>
                </div>
                <div>
                  <div class="form-label">变量指标</div>
                  <span class="badge info"><span class="badge-dot"></span> {{ metricLabel(detail.exp.variable_metric) }}</span>
                </div>
                <div v-if="detail.groupRole">
                  <div class="form-label">你的小组角色</div>
                  <span class="badge" :class="detail.groupRole.role === 'experimental' ? 'info' : 'warning'">
                    <span class="badge-dot"></span> {{ detail.groupRole.role === 'experimental' ? '实验组' : '对照组' }}
                  </span>
                </div>
                <div v-if="detail.groupRole?.variable_target">
                  <div class="form-label">变量目标</div>
                  <span>{{ detail.groupRole.variable_target }}</span>
                </div>
              </div>

              <div v-if="detail.exp.hypothesis" style="margin-top:12px">
                <strong>实验假设：</strong>{{ detail.exp.hypothesis }}
              </div>
              <div v-if="detail.exp.conclusion" style="margin-top:8px">
                <strong>实验结论：</strong>{{ detail.exp.conclusion }}
              </div>

              <div style="margin-top: 20px; border-top: 1px solid var(--line); padding-top: 16px">
                <h4 style="margin-bottom: 8px">记录观察</h4>
                <label>
                  <div class="form-label">观察内容</div>
                  <textarea
                    v-model="detail.newContent"
                    class="input textarea"
                    rows="3"
                    placeholder="记录你今天观察到的现象..."
                  ></textarea>
                </label>
                <button class="btn primary sm" style="margin-top: 8px" @click="submitObservation" :disabled="!detail.newContent.trim() || detail.submitting">
                  {{ detail.submitting ? '提交中...' : '提交观察' }}
                </button>
                <div v-if="detail.msg" class="msg-success" style="margin-top:8px">{{ detail.msg }}</div>
              </div>

              <div style="margin-top: 20px; border-top: 1px solid var(--line); padding-top: 16px">
                <h4 style="margin-bottom: 8px">观察记录历史</h4>
                <table class="table" v-if="detail.observations.length">
                  <thead>
                    <tr><th>学生</th><th>内容</th><th>时间</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="obs in detail.observations" :key="obs.id">
                      <td>#{{ obs.student_id }}</td>
                      <td>{{ obs.content || '-' }}</td>
                      <td>{{ obs.recorded_at.slice(0, 19).replace('T', ' ') }}</td>
                    </tr>
                  </tbody>
                </table>
                <EmptyState v-else compact icon="leaf" title="暂无观察记录" />
              </div>
            </div>
          </div>
        </div>
      </Teleport>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import EmptyState from '@/components/EmptyState.vue'
import { fetchMyExperiments, fetchMyExperimentGroup, fetchMyExperimentObservations, createMyExperimentObservation } from '@/api/student'
import type { Experiment, ExperimentGroup, ExperimentObservation, SensorMetric } from '@/types'

const loading = ref(true)
const experiments = ref<Experiment[]>([])
const error = ref('')
const expGroupMap = reactive<Record<number, ExperimentGroup>>({})

const metricLabels: Record<SensorMetric, string> = {
  air_temp: '空气温度',
  air_humidity: '空气湿度',
  soil_humidity: '土壤湿度',
  light_intensity: '光照强度',
  soil_ph: '土壤 pH',
  co2: 'CO₂浓度',
}
function metricLabel(m: SensorMetric) { return metricLabels[m] ?? m }

const detail = reactive({
  exp: null as Experiment | null,
  groupRole: null as ExperimentGroup | null,
  observations: [] as ExperimentObservation[],
  newContent: '',
  submitting: false,
  msg: '',
})

async function loadData() {
  loading.value = true
  try {
    experiments.value = await fetchMyExperiments()
    // Load group role for each experiment
    for (const exp of experiments.value) {
      try {
        const group = await fetchMyExperimentGroup(exp.id)
        if (group) {
          expGroupMap[exp.id] = group
        }
      } catch { /* ignore */ }
    }
  } catch (err) {
    error.value = '实验数据加载失败。'
    console.error('Failed to load experiments:', err)
  } finally {
    loading.value = false
  }
}

async function openDetail(exp: Experiment) {
  detail.exp = exp
  detail.newContent = ''
  detail.msg = ''
  try {
    const [obs, group] = await Promise.all([
      fetchMyExperimentObservations(exp.id),
      fetchMyExperimentGroup(exp.id),
    ])
    detail.observations = obs
    detail.groupRole = group
  } catch {
    detail.observations = []
    detail.groupRole = null
  }
}

function closeDetail() { detail.exp = null }

async function submitObservation() {
  if (!detail.exp || !detail.newContent.trim()) return
  detail.submitting = true
  try {
    await createMyExperimentObservation(detail.exp.id, { content: detail.newContent.trim() })
    detail.msg = '观察记录提交成功'
    detail.newContent = ''
    // Refresh observations
    const obs = await fetchMyExperimentObservations(detail.exp.id)
    detail.observations = obs
  } catch {
    detail.msg = '提交失败，请重试'
  } finally {
    detail.submitting = false
  }
}

onMounted(loadData)
</script>
