<template>
  <div class="content-area">
    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="error" class="msg-error" style="margin-bottom: 12px">{{ error }}</div>
    <template v-else>
      <div v-if="submissions.length === 0" class="empty-state">你还没有提交过作业</div>
      <div v-else class="submission-list">
        <article v-for="sub in submissions" :key="sub.id" class="content-card submission-card">
          <div class="card-header">
            <h2 class="card-title">作业 #{{ sub.id }}</h2>
            <div class="submission-badges">
              <span v-if="sub.score !== null" class="badge success">{{ sub.score }}分</span>
              <span v-else class="badge warning">待批阅</span>
            </div>
          </div>

          <div v-if="sub.content" class="submission-content">
            <div class="form-label">我的提交：</div>
            <p class="submission-text">{{ sub.content }}</p>
          </div>

          <!-- Files display -->
          <div v-if="sub.files && sub.files.length > 0" class="submission-files">
            <div class="form-label">附件（{{ sub.files.length }}）：</div>
            <div class="file-list">
              <div v-for="file in sub.files" :key="file.id" class="file-item">
                <img
                  v-if="isImageType(file.file_type)"
                  :src="file.file_url"
                  class="file-thumb"
                  @click="previewImage(file)"
                  :title="file.original_name"
                />
                <span v-else class="file-icon-box">{{ fileTypeLabel(file.file_type) }}</span>
                <a
                  :href="file.file_url"
                  :download="file.original_name"
                  class="file-name link"
                  :title="file.original_name"
                >
                  {{ file.original_name }}
                </a>
                <span class="file-size">{{ formatFileSize(file.file_size) }}</span>
              </div>
            </div>
          </div>

          <div class="submission-meta">
            <span class="meta-item">提交时间：{{ formatTime(sub.submitted_at) }}</span>
            <span v-if="sub.reviewed_at" class="meta-item">批阅时间：{{ formatTime(sub.reviewed_at) }}</span>
          </div>

          <div v-if="sub.feedback" class="feedback-box">
            <div class="feedback-label">老师反馈：</div>
            <div class="feedback-content">{{ sub.feedback }}</div>
          </div>
        </article>
      </div>

      <!-- Image preview modal -->
      <Teleport to="body">
        <div v-if="previewFile" class="modal-overlay" @click.self="previewFile = null">
          <div class="preview-modal">
            <button class="btn ghost sm preview-close" @click="previewFile = null">关闭</button>
            <img :src="previewFile.file_url" :alt="previewFile.original_name" class="preview-img" />
            <div class="preview-name">{{ previewFile.original_name }}</div>
          </div>
        </div>
      </Teleport>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchMySubmissions } from '@/api/student'
import type { SubmissionFile, TaskSubmission } from '@/types'

const loading = ref(true)
const submissions = ref<TaskSubmission[]>([])
const error = ref('')
const previewFile = ref<SubmissionFile | null>(null)

function formatTime(iso: string): string {
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function isImageType(mime: string): boolean {
  return mime.startsWith('image/')
}

function fileTypeLabel(mime: string): string {
  if (mime.startsWith('image/')) return 'IMG'
  if (mime.includes('pdf')) return 'PDF'
  if (mime.includes('powerpoint') || mime.includes('presentation')) return 'PPT'
  if (mime.includes('word') || mime.includes('document')) return 'DOC'
  if (mime.includes('text')) return 'TXT'
  if (mime.startsWith('video/')) return 'VID'
  return 'FILE'
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function previewImage(file: SubmissionFile) {
  previewFile.value = file
}

async function loadData() {
  loading.value = true
  try {
    submissions.value = await fetchMySubmissions()
  } catch (err) {
    error.value = '作业列表加载失败。'
    console.error('Failed to load submissions:', err)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>
