<template>
  <div class="content-area">
    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="error" class="msg-error" style="margin-bottom: 12px">{{ error }}</div>
    <template v-else>
      <div v-if="tasks.length === 0" class="empty-state">老师还没有给你布置任务</div>
      <div v-else class="task-list-vertical">
        <article v-for="task in tasks" :key="task.id" class="content-card task-card">
          <div class="task-card-header">
            <h2 class="card-title">{{ task.title }}</h2>
            <div class="task-badges">
              <span v-if="task.status === 'pending'" class="badge warning"><span class="badge-dot"></span> 待完成</span>
              <span v-else-if="task.status === 'in_progress'" class="badge info"><span class="badge-dot"></span> 进行中</span>
              <span v-else class="badge success"><span class="badge-dot"></span> 已完成</span>
              <span v-if="task.task_type" class="badge muted">{{ taskTypeLabel(task.task_type) }}</span>
              <span v-if="task.course_subject === 'science'" class="badge info">科学课</span>
              <span v-else-if="task.course_subject === 'labor'" class="badge warning">劳动课</span>
            </div>
          </div>

          <p v-if="task.description" class="task-description">{{ task.description }}</p>

          <div class="task-meta-row">
            <span v-if="task.assigned_date" class="meta-item">布置日期：{{ task.assigned_date }}</span>
            <span v-if="task.due_date" class="meta-item">截止日期：{{ task.due_date }}</span>
          </div>

          <div class="task-card-footer">
            <div v-if="submissionMap[task.id]" class="submission-status">
              <span v-if="submissionMap[task.id].score !== null" class="badge success">
                已批阅 · {{ submissionMap[task.id].score }}分
              </span>
              <span v-else class="badge info">已提交，等待批阅</span>
            </div>
            <button class="btn primary sm" @click="openSubmit(task)">
              {{ submissionMap[task.id] ? '修改作业' : '提交作业' }}
            </button>
          </div>

          <div v-if="submissionMap[task.id]?.feedback" class="feedback-box">
            <div class="feedback-label">老师反馈：</div>
            <div class="feedback-content">{{ submissionMap[task.id]?.feedback }}</div>
          </div>
        </article>
      </div>

      <Teleport to="body">
        <div v-if="submitDialog.task" class="modal-overlay" @click.self="closeSubmit">
          <div class="modal-card">
            <div class="modal-header">
              <h3>提交作业：{{ submitDialog.task.title }}</h3>
              <button class="btn ghost sm" @click="closeSubmit">关闭</button>
            </div>
            <div class="modal-body">
              <!-- Existing files display (read-only for re-submission) -->
              <div v-if="submitDialog.existingFiles.length > 0" class="existing-files-notice">
                <div class="form-label">当前已有附件（{{ submitDialog.existingFiles.length }}个）</div>
                <p class="re-submit-hint">重新提交将替换所有文件，请重新上传。</p>
                <div class="file-list">
                  <div v-for="f in submitDialog.existingFiles" :key="f.id" class="file-item">
                    <span class="file-icon">{{ fileTypeEmoji(f.file_type) }}</span>
                    <span class="file-name">{{ f.original_name }}</span>
                    <span class="file-size">{{ formatFileSize(f.file_size) }}</span>
                  </div>
                </div>
              </div>

              <!-- File upload area -->
              <div>
                <div class="form-label">上传附件（{{ submitDialog.files.length }}/10）</div>
                <div
                  class="upload-zone"
                  @click="triggerFileInput"
                  @dragover.prevent="dragOver = true"
                  @dragleave.prevent="dragOver = false"
                  @drop.prevent="handleDrop"
                  :class="{ 'upload-zone-active': dragOver }"
                >
                  <div class="upload-icon">📎</div>
                  <div class="upload-text">点击或拖拽文件到此处上传</div>
                  <div class="upload-hint">支持图片(jpg/png/webp/gif)、文档(pdf/ppt/doc/txt)、视频(mp4)，单个文件最大 20MB</div>
                </div>
                <input
                  ref="fileInput"
                  type="file"
                  multiple
                  style="display: none"
                  @change="handleFileChange"
                  accept="image/jpeg,image/png,image/webp,image/gif,application/pdf,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,video/mp4"
                />
              </div>

              <!-- Selected files list -->
              <div v-if="submitDialog.files.length > 0" class="file-list">
                <div v-for="(f, idx) in submitDialog.files" :key="idx" class="file-item">
                  <span class="file-icon">{{ fileTypeEmoji(f.type || '') }}</span>
                  <span class="file-name">{{ f.name }}</span>
                  <span class="file-size">{{ formatFileSize(f.size) }}</span>
                  <button class="file-remove-btn" @click="removeFile(idx)" title="移除">✕</button>
                </div>
              </div>

              <!-- Text content (optional) -->
              <label>
                <div class="form-label">补充说明（可选）</div>
                <textarea
                  v-model="submitDialog.content"
                  class="input textarea"
                  rows="4"
                  placeholder="对提交文件的简要说明..."
                ></textarea>
              </label>
            </div>
            <div class="modal-footer">
              <button class="btn ghost" @click="closeSubmit">取消</button>
              <button class="btn primary" :disabled="submitDialog.loading || !canSubmit" @click="handleSubmit">
                {{ submitDialog.loading ? '提交中...' : '提交' }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { fetchMyTasks, fetchMySubmissions, submitMyTask } from '@/api/student'
import type { ClassTask, SubmissionFile, TaskSubmission, TaskType } from '@/types'

const loading = ref(true)
const tasks = ref<ClassTask[]>([])
const submissions = ref<TaskSubmission[]>([])
const error = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const dragOver = ref(false)

const submissionMap = reactive<Record<number, TaskSubmission>>({})

const submitDialog = reactive({
  task: null as ClassTask | null,
  content: '',
  files: [] as File[],
  existingFiles: [] as SubmissionFile[],
  loading: false,
})

const canSubmit = computed(() => {
  return submitDialog.content.trim() !== '' || submitDialog.files.length > 0
})

const MAX_FILES = 10
const MAX_SIZE = 20 * 1024 * 1024

const taskTypeLabels: Record<TaskType, string> = {
  observation: '观察任务',
  experiment: '实验任务',
  maintenance: '维护任务',
}

function taskTypeLabel(type: TaskType | null): string {
  return type ? taskTypeLabels[type] : ''
}

function fileTypeEmoji(mime: string): string {
  if (mime.startsWith('image/')) return '🖼️'
  if (mime.includes('pdf')) return '📕'
  if (mime.includes('powerpoint') || mime.includes('presentation')) return '📊'
  if (mime.includes('word') || mime.includes('document')) return '📝'
  if (mime.includes('text')) return '📄'
  if (mime.startsWith('video/')) return '🎬'
  return '📎'
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function loadData() {
  loading.value = true
  try {
    const [t, s] = await Promise.all([fetchMyTasks(), fetchMySubmissions()])
    tasks.value = t
    submissions.value = s
    for (const sub of s) {
      submissionMap[sub.task_id] = sub
    }
  } catch (err) {
    error.value = '任务加载失败，请确认后端已启动。'
    console.error('Failed to load tasks:', err)
  } finally {
    loading.value = false
  }
}

function openSubmit(task: ClassTask) {
  submitDialog.task = task
  const existing = submissionMap[task.id]
  submitDialog.content = existing?.content ?? ''
  submitDialog.files = []
  submitDialog.existingFiles = existing?.files ?? []
}

function closeSubmit() {
  submitDialog.task = null
  submitDialog.content = ''
  submitDialog.files = []
  submitDialog.existingFiles = []
}

function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files) {
    addFiles(Array.from(input.files))
    input.value = ''
  }
}

function handleDrop(event: DragEvent) {
  dragOver.value = false
  if (event.dataTransfer?.files) {
    addFiles(Array.from(event.dataTransfer.files))
  }
}

function addFiles(newFiles: File[]) {
  for (const f of newFiles) {
    if (submitDialog.files.length >= MAX_FILES) {
      alert(`最多只能上传 ${MAX_FILES} 个文件`)
      break
    }
    if (f.size > MAX_SIZE) {
      alert(`文件 "${f.name}" 超过 20MB 限制`)
      continue
    }
    submitDialog.files.push(f)
  }
}

function removeFile(index: number) {
  submitDialog.files.splice(index, 1)
}

async function handleSubmit() {
  if (!submitDialog.task || !canSubmit.value) return
  submitDialog.loading = true
  try {
    const fd = new FormData()
    if (submitDialog.content.trim()) {
      fd.append('content', submitDialog.content.trim())
    }
    for (const file of submitDialog.files) {
      fd.append('files', file)
    }
    const result = await submitMyTask(submitDialog.task.id, fd)
    submissionMap[result.task_id] = result
    closeSubmit()
  } catch (err) {
    console.error('Failed to submit:', err)
    alert('提交失败，请重试')
  } finally {
    submitDialog.loading = false
  }
}

onMounted(loadData)
</script>
