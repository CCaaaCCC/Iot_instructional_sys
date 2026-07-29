<template>
  <div class="grid" style="gap: 18px">
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">新增规则</h3>
          <div class="card-subtitle">例如：温度高于 30℃ 自动打开风扇</div>
        </div>
      </template>
      <form class="form-grid" @submit.prevent="handleCreate">
        <label>
          <div class="form-label">规则名称</div>
          <input v-model="form.name" class="input" placeholder="请输入规则名称" />
        </label>
        <label>
          <div class="form-label">监控指标</div>
          <select v-model="form.metric" class="select">
            <option value="air_temp">air_temp - 空气温度</option>
            <option value="air_humidity">air_humidity - 空气湿度</option>
            <option value="soil_humidity">soil_humidity - 土壤湿度</option>
            <option value="light_intensity">light_intensity - 光照强度</option>
            <option value="soil_ph">soil_ph - 土壤pH</option>
            <option value="co2">co2 - CO₂浓度</option>
          </select>
        </label>
        <label>
          <div class="form-label">比较运算符</div>
          <select v-model="form.operator" class="select">
            <option value=">">&gt; 大于</option>
            <option value=">=">&gt;= 大于等于</option>
            <option value="<">&lt; 小于</option>
            <option value="<=">&lt;= 小于等于</option>
          </select>
        </label>
        <label>
          <div class="form-label">阈值</div>
          <input v-model.number="form.threshold" class="input" type="number" step="0.1" placeholder="阈值" />
        </label>
        <label>
          <div class="form-label">动作组件类型</div>
          <select v-model="form.action_component_type" class="select">
            <option value="fan">fan - 风扇</option>
            <option value="pump">pump - 水泵</option>
            <option value="light">light - 补光灯</option>
            <option value="sensor">sensor - 传感器</option>
          </select>
        </label>
        <label>
          <div class="form-label">执行动作</div>
          <select v-model="form.action" class="select">
            <option value="on">on - 开启</option>
            <option value="off">off - 关闭</option>
            <option value="auto">auto - 自动</option>
          </select>
        </label>
        <label>
          <div class="form-label">描述</div>
          <input v-model="form.description" class="input" placeholder="可选，规则描述" />
        </label>
        <div style="display:flex;align-items:flex-end">
          <button class="btn primary">创建规则</button>
        </div>
      </form>
    </SectionCard>

    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">规则列表</h3>
          <div class="card-subtitle">启用、停用并跟踪规则配置</div>
        </div>
        <button class="btn secondary sm" @click="loadRules">刷新</button>
      </template>
      <table class="table">
        <thead>
          <tr>
            <th>名称</th>
            <th>条件</th>
            <th>动作</th>
            <th>状态</th>
            <th>描述</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="rule in rules" :key="rule.id">
            <td><strong>{{ rule.name }}</strong></td>
            <td>{{ rule.metric }} {{ rule.operator }} {{ rule.threshold }}</td>
            <td>{{ rule.action_component_type }} → {{ rule.action }}</td>
            <td><span class="badge" :class="rule.enabled ? 'success' : 'danger'"><span class="badge-dot"></span> {{ rule.enabled ? '启用' : '停用' }}</span></td>
            <td>{{ rule.description || '-' }}</td>
            <td>
              <div class="actions">
                <button class="btn secondary sm" @click="toggle(rule.id)">{{ rule.enabled ? '停用' : '启用' }}</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="message" class="msg-success">{{ message }}</div>
      <div v-if="error" class="msg-error">{{ error }}</div>
    </SectionCard>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import { createRule, fetchRules, toggleRule } from '@/api/rules'
import type { ComponentStatus, ComponentType, Rule, RuleOperator, SensorMetric } from '@/types'

const rules = ref<Rule[]>([])
const message = ref('')
const error = ref('')
const form = reactive({
  name: '',
  metric: 'air_temp' as SensorMetric,
  operator: '>' as RuleOperator,
  threshold: 30,
  action_component_type: 'fan' as ComponentType,
  action: 'on' as ComponentStatus,
  description: '',
})

async function loadRules() {
  rules.value = await fetchRules()
}

async function handleCreate() {
  message.value = ''
  error.value = ''
  try {
    await createRule({
      ...form,
      description: form.description || null,
    })
    message.value = '规则创建成功'
    await loadRules()
  } catch {
    error.value = '规则创建失败，请确认字段有效。'
  }
}

async function toggle(ruleId: number) {
  try {
    await toggleRule(ruleId)
    await loadRules()
  } catch {
    error.value = '规则切换失败。'
  }
}

onMounted(loadRules)
</script>
