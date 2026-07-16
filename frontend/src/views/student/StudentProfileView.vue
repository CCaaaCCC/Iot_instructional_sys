<template>
  <div class="content-area">
    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="error" class="msg-error" style="margin-bottom: 12px">{{ error }}</div>
    <template v-else>
      <section class="content-card profile-hero">
        <div class="profile-avatar-wrapper">
          <div class="profile-avatar">
            <img v-if="avatarSrc" :src="avatarSrc" :alt="displayName" @error="onAvatarError" />
            <span v-else class="avatar-fallback">{{ initial }}</span>
          </div>
          <label class="avatar-upload-btn" title="更换头像">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
            <input type="file" accept="image/jpeg,image/png,image/webp" @change="handleAvatarUpload" hidden />
          </label>
        </div>
        <div class="profile-info">
          <h2 class="profile-name">{{ displayName }}</h2>
          <div class="profile-meta">
            <span class="badge muted">{{ auth.user?.username }}</span>
            <span v-if="group" class="badge info">{{ group.name }}</span>
            <span class="badge success">学生</span>
          </div>
          <div class="profile-joined">加入时间：{{ formatDate(auth.user?.created_at ?? '') }}</div>
        </div>
      </section>

      <section class="content-card">
        <div class="card-header">
          <h2 class="card-title">修改昵称</h2>
        </div>
        <div class="form-grid">
          <label>
            <div class="form-label">昵称</div>
            <input v-model="profileForm.displayName" class="input" placeholder="输入新的昵称" maxlength="50" />
          </label>
        </div>
        <div class="form-actions">
          <button class="btn primary" :disabled="profileForm.loading" @click="handleSaveProfile">
            {{ profileForm.loading ? '保存中...' : '保存昵称' }}
          </button>
        </div>
      </section>

      <section class="content-card">
        <div class="card-header">
          <h2 class="card-title">修改密码</h2>
        </div>
        <div class="form-grid">
          <label>
            <div class="form-label">旧密码</div>
            <input v-model="passwordForm.oldPassword" type="password" class="input" placeholder="输入当前密码" />
          </label>
          <label>
            <div class="form-label">新密码</div>
            <input v-model="passwordForm.newPassword" type="password" class="input" placeholder="至少8位，含字母和数字" />
          </label>
          <label>
            <div class="form-label">确认新密码</div>
            <input v-model="passwordForm.confirmPassword" type="password" class="input" placeholder="再次输入新密码" />
          </label>
        </div>
        <div v-if="passwordForm.error" class="msg-error" style="margin-top: 8px">{{ passwordForm.error }}</div>
        <div v-if="passwordForm.success" class="msg-success" style="margin-top: 8px">{{ passwordForm.success }}</div>
        <div class="form-actions">
          <button class="btn primary" :disabled="passwordForm.loading" @click="handleChangePassword">
            {{ passwordForm.loading ? '修改中...' : '修改密码' }}
          </button>
        </div>
      </section>

      <section class="content-card">
        <div class="card-header">
          <h2 class="card-title">学习统计</h2>
        </div>
        <div class="stat-grid">
          <div class="stat-card">
            <div class="stat-value">{{ tasks.length }}</div>
            <div class="stat-label">总任务数</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ pendingCount }}</div>
            <div class="stat-label">待完成任务</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ submissions.length }}</div>
            <div class="stat-label">已交作业</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ reviewedCount }}</div>
            <div class="stat-label">已批阅</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ avgScore !== null ? avgScore.toFixed(1) : '--' }}</div>
            <div class="stat-label">平均分</div>
          </div>
          <div class="stat-card" v-if="analytics">
            <div class="stat-value">{{ analytics.completion_rate }}%</div>
            <div class="stat-label">完成率</div>
          </div>
          <div class="stat-card" v-if="analytics">
            <div class="stat-value">{{ analytics.on_time_count }} / {{ analytics.total_submissions || 0 }}</div>
            <div class="stat-label">按时提交</div>
          </div>
          <div class="stat-card" v-if="analytics">
            <div class="stat-value">{{ analytics.on_time_ratio }}%</div>
            <div class="stat-label">按时率</div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { fetchMyGroup, fetchMySubmissions, fetchMyTasks, updateMyProfile, changeMyPassword, uploadMyAvatar } from '@/api/student'
import { fetchMyAnalytics } from '@/api/analytics'
import type { ClassTask, Group, TaskSubmission, StudentAnalyticsSummary } from '@/types'

const auth = useAuthStore()
const loading = ref(true)
const error = ref('')
const group = ref<Group | null>(null)
const tasks = ref<ClassTask[]>([])
const submissions = ref<TaskSubmission[]>([])
const analytics = ref<StudentAnalyticsSummary | null>(null)
const avatarError = ref(false)

const profileForm = reactive({
  displayName: '',
  loading: false,
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
  loading: false,
  error: '',
  success: '',
})

const displayName = computed(() => auth.user?.display_name || auth.user?.username || '同学')
const initial = computed(() => displayName.value.charAt(0).toUpperCase())
const avatarSrc = computed(() => {
  if (avatarError.value) return ''
  const url = auth.user?.avatar_url
  if (!url) return ''
  if (url.startsWith('http')) return url
  return url
})

const pendingCount = computed(() =>
  tasks.value.filter((t) => t.status === 'pending' || t.status === 'in_progress').length,
)
const reviewedCount = computed(() =>
  submissions.value.filter((s) => s.score !== null).length,
)
const avgScore = computed(() => {
  const scored = submissions.value.filter((s) => s.score !== null)
  if (scored.length === 0) return null
  return scored.reduce((sum, s) => sum + (s.score ?? 0), 0) / scored.length
})

function formatDate(iso: string): string {
  if (!iso) return '--'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function onAvatarError() {
  avatarError.value = true
}

async function handleAvatarUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    alert('头像文件不能超过 2MB')
    input.value = ''
    return
  }
  try {
    const result = await uploadMyAvatar(file)
    auth.updateProfile({ avatar_url: result.avatar_url })
    avatarError.value = false
  } catch (err) {
    console.error('Failed to upload avatar:', err)
    alert('头像上传失败，请检查文件格式（仅支持 jpg/png/webp）')
  }
  input.value = ''
}

async function handleSaveProfile() {
  const name = profileForm.displayName.trim()
  if (!name) {
    alert('昵称不能为空')
    return
  }
  profileForm.loading = true
  try {
    const updated = await updateMyProfile({ display_name: name })
    auth.updateProfile({ display_name: updated.display_name })
  } catch (err) {
    console.error('Failed to update profile:', err)
    alert('保存失败，请重试')
  } finally {
    profileForm.loading = false
  }
}

function validatePassword(password: string): string | null {
  if (password.length < 8) return '新密码至少 8 位'
  if (!/[A-Za-z]/.test(password)) return '新密码必须包含字母'
  if (!/\d/.test(password)) return '新密码必须包含数字'
  return null
}

async function handleChangePassword() {
  passwordForm.error = ''
  passwordForm.success = ''
  if (!passwordForm.oldPassword) {
    passwordForm.error = '请输入旧密码'
    return
  }
  const validationError = validatePassword(passwordForm.newPassword)
  if (validationError) {
    passwordForm.error = validationError
    return
  }
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    passwordForm.error = '两次输入的新密码不一致'
    return
  }
  passwordForm.loading = true
  try {
    await changeMyPassword(passwordForm.oldPassword, passwordForm.newPassword)
    passwordForm.success = '密码修改成功，下次请使用新密码登录'
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    passwordForm.error = typeof detail === 'string' ? detail : '密码修改失败，请重试'
  } finally {
    passwordForm.loading = false
  }
}

async function loadData() {
  loading.value = true
  try {
    const [g, t, s, a] = await Promise.all([
      fetchMyGroup(),
      fetchMyTasks(),
      fetchMySubmissions(),
      fetchMyAnalytics().catch(() => null),
    ])
    group.value = g
    tasks.value = t
    submissions.value = s
    analytics.value = a
    profileForm.displayName = auth.user?.display_name ?? ''
  } catch (err) {
    error.value = '数据加载失败，请确认后端已启动。'
    console.error('Failed to load profile data:', err)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>
