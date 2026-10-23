<template>
  <div class="grid" style="gap: 18px">
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">批阅中心</h3>
          <div class="card-subtitle">查看学生作业提交，打分并填写评语</div>
        </div>
        <div class="toolbar">
          <select v-model="filterReviewed" class="select" style="width: 160px" @change="loadSubmissions">
            <option value="false">待批阅</option>
            <option value="true">已批阅</option>
            <option value="">全部</option>
          </select>
          <select v-model="filterTaskId" class="select" style="width: 220px" @change="loadSubmissions">
            <option :value="undefined">全部任务</option>
            <option v-for="t in tasks" :key="t.id" :value="t.id">#{{ t.id }} {{ t.title }}</option>
          </select>
          <button class="btn secondary sm" @click="loadSubmissions">刷新</button>
        </div>
      </template>

      <EmptyState
        v-if="!submissions.length"
        :icon="filterReviewed === 'false' ? 'leaf' : 'inbox'"
        :title="filterReviewed === 'false' ? '暂无待批阅提交' : '暂无提交记录'"
        :desc="filterReviewed === 'false' ? '学生提交作业后会出现在这里' : '试试切换筛选条件'"
      />

      <div v-else class="grid" style="gap: 14px">
        <div v-for="s in submissions" :key="s.id" class="submission-card">
          <div class="submission-header">
            <div class="submission-meta">
              <strong>提交 #{{ s.id }}</strong>
              <span class="badge info"><span class="badge-dot"></span> 任务：{{ taskTitle(s.task_id) }}</span>
              <span class="badge"><span class="badge-dot"></span> 学生：{{ studentLabel(s.student_id) }}</span>
              <span class="badge"><span class="badge-dot"></span> 提交时间：{{ formatTime(s.submitted_at) }}</span>
              <span v-if="s.reviewed_at" class="badge success"><span class="badge-dot"></span> 已批阅：{{ formatTime(s.reviewed_at) }}</span>
            </div>
            <div class="submission-score" v-if="s.score !== null">
              <span class="score-badge">{{ s.score }} 分</span>
            </div>
          </div>

          <div class="submission-body">
            <div class="submission-content">
              <div class="submission-label">作业内容：</div>
              <div class="submission-text">{{ s.content || '（无文字内容）' }}</div>
            </div>

            <!-- Files display -->
            <div v-if="s.files && s.files.length > 0" class="submission-content">
              <div class="submission-label">附件（{{ s.files.length }}）：</div>
              <div class="file-list">
                <div v-for="file in s.files" :key="file.id" class="file-item">
                  <img
                    v-if="isImageType(file.file_type)"
                    :src="file.file_url"
                    class="file-thumb"
                    @click="previewFile = file"
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

            <div v-if="s.feedback" class="submission-content">
              <div class="submission-label">教师评语：</div>
              <div class="submission-text feedback">{{ s.feedback }}</div>
            </div>
          </div>

          <div v-if="!isReviewed(s)" class="submission-review">
            <div class="review-title">批阅此提交</div>
            <div class="review-form">
              <label>
                <div class="form-label">评分（0-100）</div>
                <input v-model.number="reviewForms[s.id].score" class="input" type="number" min="0" max="100" step="1" style="width: 120px" />
              </label>
              <label style="flex: 1">
                <div class="form-label">评语（可选）</div>
                <input v-model="reviewForms[s.id].feedback" class="input" placeholder="如：观察细致，记录完整" />
              </label>
              <button class="btn primary" @click="handleReview(s.id)">提交批阅</button>
            </div>
          </div>
          <div v-else class="submission-reviewed">
            <span class="badge success"><span class="badge-dot"></span> 已批阅 - 得分：{{ s.score }}</span>
            <button class="btn secondary sm" @click="resetReview(s)">重新批阅</button>
          </div>
        </div>
      </div>


    </SectionCard>

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
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useToast } from '@/composables/useToast'
import { fetchSubmissions, reviewSubmission } from '@/api/submissions'
import { fetchTasks } from '@/api/tasks'
import { fetchUsers } from '@/api/users'
import type { ClassTask, SubmissionFile, TaskSubmission, User } from '@/types'

const submissions = ref<TaskSubmission[]>([])
const tasks = ref<ClassTask[]>([])
const users = ref<User[]>([])
const reviewForms = reactive<Record<number, { score: number; feedback: string }>>({})
const toast = useToast()
const filterReviewed = ref<'true' | 'false' | ''>('false')
const filterTaskId = ref<number | undefined>(undefined)
const previewFile = ref<SubmissionFile | null>(null)

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN')
}

function isReviewed(s: TaskSubmission) {
  return s.score !== null && s.reviewed_at !== null
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

function taskTitle(taskId: number) {
  const t = tasks.value.find((x) => x.id === taskId)
  return t ? `#${t.id} ${t.title}` : `#${taskId}`
}

function studentLabel(studentId: number) {
  const u = users.value.find((x) => x.id === studentId)
  return u ? `${u.username}${u.display_name ? ` (${u.display_name})` : ''}` : `#${studentId}`
}

async function loadSubmissions() {
  try {
    const params: { reviewed?: boolean; task_id?: number } = {}
    if (filterReviewed.value === 'true') params.reviewed = true
    if (filterReviewed.value === 'false') params.reviewed = false
    if (filterTaskId.value !== undefined) params.task_id = filterTaskId.value
    submissions.value = await fetchSubmissions(params)
    for (const s of submissions.value) {
      if (!isReviewed(s) && !reviewForms[s.id]) {
        reviewForms[s.id] = { score: 80, feedback: '' }
      }
    }
  } catch {
    toast.error('提交列表加载失败')
  }
}

async function loadAll() {
  try {
    const [tasksData, usersData] = await Promise.all([fetchTasks(), fetchUsers()])
    tasks.value = tasksData
    users.value = usersData
    await loadSubmissions()
  } catch {
    toast.error('基础数据加载失败')
  }
}

async function handleReview(submissionId: number) {
  const form = reviewForms[submissionId]
  if (!form) return
  if (form.score === null || form.score === undefined || form.score < 0 || form.score > 100) {
    toast.warning('评分需在 0-100 之间')
    return
  }
  try {
    await reviewSubmission(submissionId, {
      score: form.score,
      feedback: form.feedback || undefined,
    })
    toast.success(`提交 #${submissionId} 已批阅`)
    await loadSubmissions()
  } catch {
    toast.error('批阅失败，请检查评分与评语')
  }
}

function resetReview(s: TaskSubmission) {
  s.score = null
  s.reviewed_at = null
  s.feedback = null
  reviewForms[s.id] = { score: 80, feedback: '' }
}

onMounted(loadAll)
</script>

<style scoped>
.submission-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 14px 16px;
  background: var(--panel);
}
.submission-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.submission-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.submission-body {
  margin: 10px 0;
  padding: 10px 0;
  border-top: 1px dashed var(--line);
  border-bottom: 1px dashed var(--line);
  display: grid;
  gap: 8px;
}
.submission-content {
  display: grid;
  gap: 4px;
}
.submission-label {
  font-size: 13px;
  color: var(--muted);
  font-weight: 600;
}
.submission-text {
  white-space: pre-wrap;
  word-break: break-word;
}
.submission-text.feedback {
  background: var(--panel);
  padding: 8px 10px;
  border-radius: 6px;
  border-left: 3px solid var(--primary);
}
.submission-link {
  color: var(--primary);
  text-decoration: underline;
  word-break: break-all;
}
.submission-review {
  margin-top: 10px;
  padding: 10px;
  background: var(--panel);
  border-radius: 6px;
  border: 1px solid var(--line);
}
.review-title {
  font-weight: 600;
  margin-bottom: 8px;
}
.review-form {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  flex-wrap: wrap;
}
.submission-reviewed {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 10px;
}
.score-badge {
  background: var(--primary);
  color: var(--btn-primary-text);
  padding: 4px 12px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 14px;
}
</style>
