<template>
  <div class="grid" style="gap: 18px">
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">发布教学资源</h3>
          <div class="card-subtitle">上传 PPT、视频或文档资料，发布后学生端可见</div>
        </div>
      </template>
      <form class="form-grid" @submit.prevent="handleCreate">
        <label>
          <div class="form-label">资源名称 *</div>
          <input v-model="form.title" class="input" required maxlength="100" />
        </label>
        <label>
          <div class="form-label">资源类型 *</div>
          <select v-model="form.resource_type" class="select" required>
            <option value="">请选择</option>
            <option value="ppt">PPT</option>
            <option value="pdf">PDF</option>
            <option value="video">视频</option>
            <option value="doc">文档</option>
            <option value="txt">文本</option>
          </select>
        </label>
        <label>
          <div class="form-label">科目 *</div>
          <select v-model="form.subject" class="select" required>
            <option value="">请选择</option>
            <option value="labor">劳动课</option>
            <option value="science">科学课</option>
          </select>
        </label>
        <label>
          <div class="form-label">关联班级</div>
          <select v-model.number="form.classroom_id" class="select">
            <option :value="undefined">不限班级</option>
            <option v-for="c in classrooms" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </label>
        <label>
          <div class="form-label">关联小组</div>
          <select v-model.number="form.group_id" class="select">
            <option :value="undefined">不限小组</option>
            <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
        </label>
        <label>
          <div class="form-label">关联任务</div>
          <select v-model.number="form.task_id" class="select">
            <option :value="undefined">不限任务</option>
            <option v-for="t in tasks" :key="t.id" :value="t.id">{{ t.title }}</option>
          </select>
        </label>
        <label class="form-grid-span">
          <div class="form-label">描述</div>
          <input v-model="form.description" class="input" maxlength="500" />
        </label>
        <label>
          <div class="form-label">上传文件 *</div>
          <input type="file" class="input" @change="onFileChange" required accept=".pdf,.ppt,.pptx,.mp4,.doc,.docx,.txt" />
        </label>
        <label style="display:flex;align-items:flex-end;gap:10px">
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" v-model="form.is_published" />
            <span class="form-label" style="margin:0">立即发布</span>
          </label>
        </label>
        <div class="form-grid-span" style="display:flex;gap:10px">
          <button :class="['btn', 'primary', { loading: submitting }]" :disabled="submitting">上传资源</button>
        </div>
      </form>

    </SectionCard>

    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">资源列表</h3>
          <div class="card-subtitle">已发布的资源学生可在学生端查看和下载</div>
        </div>
        <div class="toolbar">
          <select v-model="filterSubject" class="select" style="width:auto">
            <option value="">全部科目</option>
            <option value="labor">劳动课</option>
            <option value="science">科学课</option>
          </select>
          <button class="btn secondary sm" @click="loadResources">刷新</button>
        </div>
      </template>
      <table class="table" v-if="resources.length">
        <thead>
          <tr>
            <th>名称</th>
            <th>类型</th>
            <th>科目</th>
            <th>范围</th>
            <th>状态</th>
            <th>下载</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in resources" :key="r.id">
            <td>
              <strong>{{ r.title }}</strong>
              <div class="card-subtitle" v-if="r.description" style="font-size:12px">{{ r.description.slice(0, 40) }}{{ r.description.length > 40 ? '...' : '' }}</div>
            </td>
            <td><span class="badge info"><span class="badge-dot"></span>{{ typeLabel(r.resource_type) }}</span></td>
            <td>{{ r.subject === 'labor' ? '劳动课' : '科学课' }}</td>
            <td style="font-size:13px">{{ scopeLabel(r) }}</td>
            <td>
              <span class="badge" :class="r.is_published ? 'success' : 'muted'">
                <span class="badge-dot"></span>
                {{ r.is_published ? '已发布' : '未发布' }}
              </span>
            </td>
            <td>{{ r.download_count }}</td>
            <td>
                <div class="actions" style="display:flex;gap:6px;flex-wrap:wrap">
                  <button class="btn secondary sm" @click="previewItem = r">预览</button>
                  <a :href="r.file_url" class="btn secondary sm" target="_blank" rel="noopener">下载</a>
                  <button class="btn secondary sm" @click="togglePublish(r)">
                    {{ r.is_published ? '撤回' : '发布' }}
                  </button>
                  <button class="btn danger sm" @click="handleDelete(r)">删除</button>
                </div>
              </td>
          </tr>
        </tbody>
      </table>
      <EmptyState
        v-else
        icon="inbox"
        title="暂无教学资源"
        desc="上传课件或资料，发布后学生即可查看"
      />
    </SectionCard>

    <FilePreviewModal v-if="previewItem" :file="previewItem" @close="previewItem = null" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import FilePreviewModal from '@/components/FilePreviewModal.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import {
  fetchResources,
  createResource,
  deleteResource,
  togglePublishResource,
} from '@/api/resources'
import { fetchClassrooms } from '@/api/classrooms'
import { fetchGroups } from '@/api/groups'
import { fetchTasks } from '@/api/tasks'
import type { TeachingResource, Classroom, Group, ClassTask } from '@/types'

const resources = ref<TeachingResource[]>([])
const classrooms = ref<Classroom[]>([])
const groups = ref<Group[]>([])
const tasks = ref<ClassTask[]>([])
const submitting = ref(false)
const confirm = useConfirm()
const toast = useToast()
const filterSubject = ref('')
const selectedFile = ref<File | null>(null)
const previewItem = ref<TeachingResource | null>(null)

const form = reactive({
  title: '',
  description: '',
  resource_type: '',
  subject: '',
  classroom_id: undefined as number | undefined,
  group_id: undefined as number | undefined,
  task_id: undefined as number | undefined,
  is_published: false,
})

function resetForm() {
  form.title = ''
  form.description = ''
  form.resource_type = ''
  form.subject = ''
  form.classroom_id = undefined
  form.group_id = undefined
  form.task_id = undefined
  form.is_published = false
  selectedFile.value = null
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

async function handleCreate() {
  if (!form.title.trim()) {
    toast.warning('请填写资源标题')
    return
  }
  if (!selectedFile.value) {
    toast.warning('请选择要上传的文件')
    return
  }
  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('title', form.title)
    if (form.description) fd.append('description', form.description)
    fd.append('resource_type', form.resource_type)
    fd.append('subject', form.subject)
    if (form.classroom_id) fd.append('classroom_id', String(form.classroom_id))
    if (form.group_id) fd.append('group_id', String(form.group_id))
    if (form.task_id) fd.append('task_id', String(form.task_id))
    fd.append('is_published', String(form.is_published))
    fd.append('file', selectedFile.value)
    await createResource(fd)
    toast.success('教学资源已上传')
    resetForm()
    await loadResources()
  } catch {
    toast.error('上传失败，请检查文件格式与大小')
  } finally {
    submitting.value = false
  }
}

async function loadResources() {
  try {
    const params: Record<string, string | number> = {}
    if (filterSubject.value) params.subject = filterSubject.value
    resources.value = await fetchResources(params)
  } catch {
    toast.error('资源列表加载失败')
  }
}

async function togglePublish(r: TeachingResource) {
  try {
    const updated = await togglePublishResource(r.id)
    const idx = resources.value.findIndex((x) => x.id === r.id)
    if (idx !== -1) resources.value[idx] = updated
    toast.success(updated.is_published ? '资源已发布，学生端可见' : '资源已撤回')
  } catch {
    toast.error('操作失败，请稍后重试')
  }
}

async function handleDelete(r: TeachingResource) {
  const ok = await confirm({
    title: '删除教学资源',
    message: `「${r.title}」及其文件将被永久删除。`,
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  try {
    await deleteResource(r.id)
    resources.value = resources.value.filter((x) => x.id !== r.id)
    toast.success('资源已删除')
  } catch {
    toast.error('删除失败，请稍后重试')
  }
}

function typeLabel(t: string) {
  const map: Record<string, string> = { ppt: 'PPT', pptx: 'PPT', pdf: 'PDF', mp4: '视频', doc: 'Word', docx: 'Word', txt: '文本' }
  return map[t] || t
}

function scopeLabel(r: TeachingResource) {
  const parts: string[] = []
  if (r.classroom_id) {
    const c = classrooms.value.find((x) => x.id === r.classroom_id)
    if (c) parts.push(c.name)
  }
  if (r.group_id) {
    const g = groups.value.find((x) => x.id === r.group_id)
    if (g) parts.push(g.name)
  }
  return parts.length ? parts.join(' / ') : '全部'
}

onMounted(async () => {
  await loadResources()
  try {
    classrooms.value = await fetchClassrooms()
    groups.value = await fetchGroups()
    tasks.value = await fetchTasks()
  } catch { /* non-critical */ }
})
</script>
