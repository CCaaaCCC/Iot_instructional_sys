<template>
  <div class="grid" style="gap: 18px">
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">新增作物</h3>
          <div class="card-subtitle">维护大棚种植档案</div>
        </div>
      </template>
      <form class="form-grid" @submit.prevent="handleCreate">
        <label>
          <div class="form-label">作物名称</div>
          <input v-model="form.name" class="input" placeholder="请输入作物名称" />
        </label>
        <label>
          <div class="form-label">生长阶段</div>
          <input v-model="form.growth_stage" class="input" placeholder="如：苗期、生长期、成熟期" />
        </label>
        <label>
          <div class="form-label">开始日期</div>
          <input v-model="form.start_date" class="input" type="date" />
        </label>
        <label>
          <div class="form-label">结束日期</div>
          <input v-model="form.end_date" class="input" type="date" />
        </label>
        <label>
          <div class="form-label">描述</div>
          <input v-model="form.description" class="input" placeholder="可选，作物描述" />
        </label>
        <label>
          <div class="form-label">备注</div>
          <input v-model="form.notes" class="input" placeholder="可选，备注信息" />
        </label>
        <div style="display:flex;align-items:flex-end">
          <button class="btn primary">创建作物</button>
        </div>
      </form>
      <div v-if="message" class="msg-success">{{ message }}</div>
      <div v-if="error" class="msg-error">{{ error }}</div>
    </SectionCard>

    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">作物列表</h3>
          <div class="card-subtitle">支持种植周期记录</div>
        </div>
        <button class="btn secondary sm" @click="loadCrops">刷新</button>
      </template>
      <table class="table">
        <thead>
          <tr>
            <th>名称</th>
            <th>阶段</th>
            <th>开始</th>
            <th>结束</th>
            <th>描述</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="crop in crops" :key="crop.id">
            <td><strong>{{ crop.name }}</strong></td>
            <td>{{ crop.growth_stage || '-' }}</td>
            <td>{{ crop.start_date || '-' }}</td>
            <td>{{ crop.end_date || '-' }}</td>
            <td>{{ crop.description || '-' }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!crops.length" class="empty-state">
        暂无作物数据
      </div>
    </SectionCard>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import { createCrop, fetchCrops } from '@/api/crops'
import type { Crop } from '@/types'

const crops = ref<Crop[]>([])
const form = reactive({ name: '', description: '', growth_stage: '', start_date: '', end_date: '', notes: '' })
const message = ref('')
const error = ref('')

async function loadCrops() {
  error.value = ''
  try {
    crops.value = await fetchCrops()
  } catch {
    error.value = '作物列表加载失败。'
  }
}

async function handleCreate() {
  message.value = ''
  error.value = ''
  try {
    await createCrop({
      ...form,
      description: form.description || null,
      growth_stage: form.growth_stage || null,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      notes: form.notes || null,
    })
    message.value = '作物创建成功'
    form.name = ''
    form.description = ''
    form.growth_stage = ''
    form.start_date = ''
    form.end_date = ''
    form.notes = ''
    await loadCrops()
  } catch {
    error.value = '作物创建失败，请确认字段有效。'
  }
}

onMounted(loadCrops)
</script>
