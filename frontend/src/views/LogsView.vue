<template>
  <div class="grid" style="gap: 18px">
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">操作日志</h3>
          <div class="card-subtitle">统一审计后台行为</div>
        </div>
        <button class="btn secondary sm" @click="loadAll">刷新</button>
      </template>
      <div v-if="error" class="msg-error" style="margin-bottom: 12px">{{ error }}</div>
      <table class="table">
        <thead>
          <tr>
            <th>时间</th>
            <th>动作</th>
            <th>实体</th>
            <th>目标 ID</th>
            <th>详情</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in operationLogs" :key="item.id">
            <td>{{ formatTime(item.created_at) }}</td>
            <td><span class="badge info"><span class="badge-dot"></span> {{ item.action }}</span></td>
            <td>{{ item.entity_type }}</td>
            <td>{{ item.entity_id || '-' }}</td>
            <td>{{ item.detail || '-' }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!operationLogs.length" class="empty-state">
        <div class="empty-state-icon">📝</div>
        暂无操作日志
      </div>
    </SectionCard>

    <div class="grid two-col">
      <SectionCard>
        <template #header>
          <div>
            <h3 class="card-title">设备日志</h3>
            <div class="card-subtitle">组件控制与规则触发记录</div>
          </div>
        </template>
        <table class="table">
          <thead>
            <tr>
              <th>时间</th>
              <th>节点</th>
              <th>组件</th>
              <th>操作</th>
              <th>信息</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in deviceLogs" :key="item.id">
              <td>{{ formatTime(item.created_at) }}</td>
              <td>{{ item.node_id ?? '-' }}</td>
              <td>{{ item.component_id ?? '-' }}</td>
              <td><span class="badge" :class="item.action === 'on' ? 'success' : item.action === 'off' ? 'danger' : 'warning'"><span class="badge-dot"></span> {{ item.action }}</span></td>
              <td>{{ item.message || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="!deviceLogs.length" class="empty-state">
          <div class="empty-state-icon">🔌</div>
          暂无设备日志
        </div>
      </SectionCard>

      <SectionCard>
        <template #header>
          <div>
            <h3 class="card-title">规则日志</h3>
            <div class="card-subtitle">自动控制触发结果</div>
          </div>
        </template>
        <table class="table">
          <thead>
            <tr>
              <th>时间</th>
              <th>规则</th>
              <th>节点</th>
              <th>组件</th>
              <th>信息</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in ruleLogs" :key="item.id">
              <td>{{ formatTime(item.triggered_at) }}</td>
              <td>{{ item.rule_id }}</td>
              <td>{{ item.node_id ?? '-' }}</td>
              <td>{{ item.component_id ?? '-' }}</td>
              <td>{{ item.message || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="!ruleLogs.length" class="empty-state">
          <div class="empty-state-icon">⚙</div>
          暂无规则日志
        </div>
      </SectionCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import { fetchDeviceLogs, fetchOperationLogs, fetchRuleLogs } from '@/api/logs'
import type { DeviceOperationLog, OperationLog, RuleLog } from '@/types'

const operationLogs = ref<OperationLog[]>([])
const deviceLogs = ref<DeviceOperationLog[]>([])
const ruleLogs = ref<RuleLog[]>([])
const error = ref('')

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN')
}

async function loadAll() {
  error.value = ''
  try {
    const [operations, devices, rules] = await Promise.all([
      fetchOperationLogs(),
      fetchDeviceLogs(),
      fetchRuleLogs(),
    ])
    operationLogs.value = operations
    deviceLogs.value = devices
    ruleLogs.value = rules
  } catch {
    error.value = '日志加载失败，请确认后端已启动。'
  }
}

onMounted(loadAll)
</script>
