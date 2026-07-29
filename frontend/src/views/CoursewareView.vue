<template>
  <div class="grid" style="gap: 18px">
    <!-- Tab switcher -->
    <div class="toolbar" style="gap:8px;margin-bottom:-8px">
      <button class="btn" :class="tab === 'my' ? 'primary' : 'secondary'" @click="tab = 'my'">我的课件</button>
      <button class="btn" :class="tab === 'public' ? 'primary' : 'secondary'" @click="tab = 'public'">公共课件库</button>
    </div>

    <!-- My Courseware -->
    <template v-if="tab === 'my'">
      <SectionCard>
        <template #header>
          <div>
            <h3 class="card-title">上传课件</h3>
            <div class="card-subtitle">支持的格式：PPT、PDF、视频、Word、文本（最大 50MB）</div>
          </div>
        </template>
        <form class="form-grid" @submit.prevent="handleCreate">
          <label>
            <div class="form-label">课件名称 *</div>
            <input v-model="form.title" class="input" required maxlength="100" />
          </label>
          <label>
            <div class="form-label">文件类型 *</div>
            <select v-model="form.file_type" class="select" required>
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
              <option value="general">通用</option>
            </select>
          </label>
          <label>
            <div class="form-label">适用年级</div>
            <select v-model="form.grade_level" class="select">
              <option value="">不限</option>
              <option value="3">三年级</option>
              <option value="4">四年级</option>
              <option value="5">五年级</option>
              <option value="6">六年级</option>
            </select>
          </label>
          <label class="form-grid-span">
            <div class="form-label">描述</div>
            <input v-model="form.description" class="input" maxlength="500" />
          </label>
          <label>
            <div class="form-label">标签（逗号分隔）</div>
            <input v-model="form.tags" class="input" maxlength="255" placeholder="如：光合作用,植物生长" />
          </label>
          <label>
            <div class="form-label">上传文件 *</div>
            <input type="file" class="input" @change="onFileChange" required accept=".pdf,.ppt,.pptx,.mp4,.doc,.docx,.txt" />
          </label>
          <label style="display:flex;align-items:flex-end;gap:10px">
            <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
              <input type="checkbox" v-model="form.is_public" />
              <span class="form-label" style="margin:0">分享到公共库</span>
            </label>
          </label>
          <div class="form-grid-span" style="display:flex;gap:10px">
            <button class="btn primary" :disabled="submitting">{{ submitting ? '上传中...' : '上传课件' }}</button>
          </div>
        </form>
        <div v-if="message" class="msg-success">{{ message }}</div>
        <div v-if="errorMsg" class="msg-error">{{ errorMsg }}</div>
      </SectionCard>

      <SectionCard>
        <template #header>
          <div>
            <h3 class="card-title">我的课件列表</h3>
            <div class="card-subtitle">管理你的个人课件</div>
          </div>
          <div class="toolbar">
            <select v-model="myFilterType" class="select" style="width:auto">
              <option value="">全部类型</option>
              <option value="ppt">PPT</option>
              <option value="pdf">PDF</option>
              <option value="video">视频</option>
              <option value="doc">文档</option>
            </select>
            <button class="btn secondary sm" @click="loadMyCourseware">刷新</button>
          </div>
        </template>
        <table class="table" v-if="myCourseware.length">
          <thead>
            <tr>
              <th>名称</th>
              <th>类型</th>
              <th>科目</th>
              <th>公开</th>
              <th>大小</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in myCourseware" :key="c.id">
              <td>
                <strong>{{ c.title }}</strong>
              </td>
              <td><span class="badge info"><span class="badge-dot"></span>{{ typeLabel(c.file_type) }}</span></td>
              <td>{{ subjectLabel(c.subject) }}</td>
              <td>
                <span class="badge" :class="c.is_public ? 'success' : 'muted'">
                  <span class="badge-dot"></span>
                  {{ c.is_public ? '公开' : '私有' }}
                </span>
              </td>
              <td>{{ formatSize(c.file_size) }}</td>
              <td>
                <div style="display:flex;gap:4px;flex-wrap:wrap">
                  <button class="btn secondary sm" @click="previewItem = c">预览</button>
                  <a :href="c.file_url" class="btn secondary sm" target="_blank" rel="noopener">下载</a>
                  <button class="btn secondary sm" @click="togglePublic(c)">{{ c.is_public ? '私密' : '公开' }}</button>
                  <button class="btn danger sm" @click="handleDelete(c)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-state">
          暂无课件，上传你的第一个课件吧
        </div>
      </SectionCard>
    </template>

    <!-- Public Courseware Library -->
    <template v-else>
      <SectionCard>
        <template #header>
          <div>
            <h3 class="card-title">公共课件库</h3>
            <div class="card-subtitle">浏览其他教师分享的课件资源</div>
          </div>
        </template>
        <div class="toolbar" style="margin-bottom:14px;flex-wrap:wrap;gap:8px">
          <select v-model="pubFilterType" class="select" style="width:auto">
            <option value="">全部类型</option>
            <option value="ppt">PPT</option>
            <option value="pdf">PDF</option>
            <option value="video">视频</option>
            <option value="doc">文档</option>
          </select>
          <select v-model="pubFilterSubject" class="select" style="width:auto">
            <option value="">全部科目</option>
            <option value="labor">劳动课</option>
            <option value="science">科学课</option>
            <option value="general">通用</option>
          </select>
          <select v-model="pubFilterGrade" class="select" style="width:auto">
            <option value="">全部年级</option>
            <option value="3">三年级</option>
            <option value="4">四年级</option>
            <option value="5">五年级</option>
            <option value="6">六年级</option>
          </select>
          <input v-model="pubSearch" class="input" style="width:160px" placeholder="搜索课件..." @keyup.enter="loadPublicCourseware" />
          <button class="btn secondary sm" @click="loadPublicCourseware">搜索</button>
        </div>
        <table class="table" v-if="publicCourseware.length">
          <thead>
            <tr>
              <th>名称</th>
              <th>类型</th>
              <th>科目</th>
              <th>年级</th>
              <th>标签</th>
              <th>上传者</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in publicCourseware" :key="c.id">
              <td>
                <strong>{{ c.title }}</strong>
                <div v-if="c.description" class="card-subtitle" style="font-size:12px">{{ c.description.slice(0, 50) }}{{ (c.description?.length || 0) > 50 ? '...' : '' }}</div>
              </td>
              <td><span class="badge info"><span class="badge-dot"></span>{{ typeLabel(c.file_type) }}</span></td>
              <td>{{ subjectLabel(c.subject) }}</td>
              <td>{{ c.grade_level ? c.grade_level + '年级' : '-' }}</td>
              <td>{{ c.tags || '-' }}</td>
              <td>{{ c.owner_name || '-' }}</td>
              <td>
                <div style="display:flex;gap:4px">
                  <button class="btn secondary sm" @click="previewItem = c">预览</button>
                  <a :href="c.file_url" class="btn secondary sm" target="_blank" rel="noopener">下载</a>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-state">
          公共课件库暂无资源
        </div>
      </SectionCard>
    </template>

    <FilePreviewModal v-if="previewItem" :file="previewItem" @close="previewItem = null" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import FilePreviewModal from '@/components/FilePreviewModal.vue'
import {
  fetchMyCourseware,
  fetchPublicCourseware,
  createCourseware,
  deleteCourseware,
  toggleCoursewarePublic,
} from '@/api/courseware'
import type { Courseware } from '@/types'

const tab = ref<'my' | 'public'>('my')
const myCourseware = ref<Courseware[]>([])
const publicCourseware = ref<Courseware[]>([])
const message = ref('')
const errorMsg = ref('')
const submitting = ref(false)
const selectedFile = ref<File | null>(null)
const previewItem = ref<Courseware | null>(null)

// Filters
const myFilterType = ref('')
const pubFilterType = ref('')
const pubFilterSubject = ref('')
const pubFilterGrade = ref('')
const pubSearch = ref('')

const form = reactive({
  title: '',
  description: '',
  file_type: '',
  subject: '',
  grade_level: '',
  tags: '',
  is_public: false,
})

function resetForm() {
  form.title = ''
  form.description = ''
  form.file_type = ''
  form.subject = ''
  form.grade_level = ''
  form.tags = ''
  form.is_public = false
  selectedFile.value = null
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

async function handleCreate() {
  if (!selectedFile.value) {
    errorMsg.value = '请选择文件'
    return
  }
  message.value = ''
  errorMsg.value = ''
  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('title', form.title)
    if (form.description) fd.append('description', form.description)
    fd.append('file_type', form.file_type)
    fd.append('subject', form.subject)
    if (form.grade_level) fd.append('grade_level', form.grade_level)
    if (form.tags) fd.append('tags', form.tags)
    fd.append('is_public', String(form.is_public))
    fd.append('file', selectedFile.value)
    await createCourseware(fd)
    message.value = '课件上传成功！'
    resetForm()
    await loadMyCourseware()
    if (form.is_public) await loadPublicCourseware()
  } catch {
    errorMsg.value = '上传失败。'
  } finally {
    submitting.value = false
  }
}

async function loadMyCourseware() {
  errorMsg.value = ''
  try {
    const params: Record<string, string> = {}
    if (myFilterType.value) params.file_type = myFilterType.value
    myCourseware.value = await fetchMyCourseware(params)
  } catch {
    errorMsg.value = '加载课件列表失败。'
  }
}

async function loadPublicCourseware() {
  errorMsg.value = ''
  try {
    const params: Record<string, string> = {}
    if (pubFilterType.value) params.file_type = pubFilterType.value
    if (pubFilterSubject.value) params.subject = pubFilterSubject.value
    if (pubFilterGrade.value) params.grade_level = pubFilterGrade.value
    if (pubSearch.value) params.search = pubSearch.value
    publicCourseware.value = await fetchPublicCourseware(params)
  } catch {
    errorMsg.value = '加载公共课件库失败。'
  }
}

async function togglePublic(c: Courseware) {
  try {
    const updated = await toggleCoursewarePublic(c.id)
    const idx = myCourseware.value.findIndex((x) => x.id === c.id)
    if (idx !== -1) myCourseware.value[idx] = updated
  } catch {
    errorMsg.value = '操作失败。'
  }
}

async function handleDelete(c: Courseware) {
  if (!confirm(`确定要删除 "${c.title}" 吗？`)) return
  try {
    await deleteCourseware(c.id)
    myCourseware.value = myCourseware.value.filter((x) => x.id !== c.id)
  } catch {
    errorMsg.value = '删除失败。'
  }
}

function typeLabel(t: string) {
  const map: Record<string, string> = { ppt: 'PPT', pptx: 'PPT', pdf: 'PDF', video: '视频', mp4: '视频', doc: 'Word', docx: 'Word', txt: '文本' }
  return map[t] || t
}

function subjectLabel(s: string) {
  const map: Record<string, string> = { labor: '劳动课', science: '科学课', general: '通用' }
  return map[s] || s
}

function formatSize(bytes: number | null) {
  if (!bytes) return ''
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

onMounted(() => {
  loadMyCourseware()
  loadPublicCourseware()
})
</script>
