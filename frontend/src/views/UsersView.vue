<template>
  <div class="grid" style="gap: 18px">
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">新增用户</h3>
          <div class="card-subtitle">仅管理员可访问后端接口，可创建管理员/教师/操作员账号</div>
        </div>
      </template>
      <form class="form-grid" @submit.prevent="handleCreate">
        <label>
          <div class="form-label">用户名</div>
          <input v-model="form.username" class="input" placeholder="请输入用户名" />
        </label>
        <label>
          <div class="form-label">显示名称</div>
          <input v-model="form.display_name" class="input" placeholder="可选，如：王老师" />
        </label>
        <label>
          <div class="form-label">初始密码</div>
          <input v-model="form.password" type="password" class="input" placeholder="至少 8 位且含字母+数字" />
        </label>
        <label>
          <div class="form-label">角色</div>
          <select v-model="form.role" class="select">
            <option value="admin">admin - 管理员</option>
            <option value="teacher">teacher - 教师</option>
            <option value="operator">operator - 操作员</option>
          </select>
        </label>
        <label>
          <div class="form-label">状态</div>
          <select v-model="form.is_active" class="select">
            <option :value="true">启用</option>
            <option :value="false">禁用</option>
          </select>
        </label>
        <div style="display:flex;align-items:flex-end">
          <button class="btn primary">创建用户</button>
        </div>
      </form>
      <div v-if="message" class="msg-success">{{ message }}</div>
      <div v-if="error" class="msg-error">{{ error }}</div>
    </SectionCard>

    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">用户列表</h3>
          <div class="card-subtitle">管理后台账号（学生账号请通过"班级小组"页面批量创建）</div>
        </div>
        <div class="toolbar">
          <select v-model="filterRole" class="select" style="width: 140px" @change="filterUsers">
            <option value="">全部角色</option>
            <option value="admin">admin</option>
            <option value="teacher">teacher</option>
            <option value="operator">operator</option>
            <option value="student">student</option>
          </select>
          <button class="btn secondary sm" @click="loadUsers">刷新</button>
        </div>
      </template>
      <table class="table">
        <thead>
          <tr>
            <th>用户名</th>
            <th>显示名称</th>
            <th>角色</th>
            <th>所属小组</th>
            <th>状态</th>
            <th>创建时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in filteredUsers" :key="user.id">
            <td><strong>{{ user.username }}</strong></td>
            <td>{{ user.display_name || '-' }}</td>
            <td><span class="badge" :class="roleClass(user.role)"><span class="badge-dot"></span> {{ roleLabel(user.role) }}</span></td>
            <td>{{ user.group_id ? `#${user.group_id}` : '-' }}</td>
            <td><span class="badge" :class="user.is_active ? 'success' : 'danger'"><span class="badge-dot"></span> {{ user.is_active ? '启用' : '禁用' }}</span></td>
            <td>{{ formatTime(user.created_at) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!filteredUsers.length" class="empty-state">
        <div class="empty-state-icon">👤</div>
        暂无用户数据
      </div>
    </SectionCard>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import { createUser, fetchUsers } from '@/api/users'
import type { User, UserRole } from '@/types'

const users = ref<User[]>([])
const message = ref('')
const error = ref('')
const filterRole = ref<UserRole | ''>('')

const form = reactive({
  username: '',
  display_name: '',
  password: '',
  role: 'teacher' as UserRole,
  is_active: true,
})

const filteredUsers = computed(() => {
  if (!filterRole.value) return users.value
  return users.value.filter((u) => u.role === filterRole.value)
})

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN')
}

function roleClass(role: UserRole) {
  if (role === 'admin') return 'warning'
  if (role === 'teacher') return 'info'
  if (role === 'operator') return ''
  if (role === 'student') return 'success'
  return ''
}

function roleLabel(role: UserRole) {
  const map: Record<UserRole, string> = {
    admin: '管理员',
    teacher: '教师',
    operator: '操作员',
    student: '学生',
  }
  return `${role} - ${map[role]}`
}

function filterUsers() {
  // computed 自动响应，此处占位避免模板警告
}

async function loadUsers() {
  message.value = ''
  error.value = ''
  try {
    users.value = await fetchUsers()
  } catch {
    error.value = '用户列表加载失败，请确认当前账号为管理员。'
  }
}

async function handleCreate() {
  message.value = ''
  error.value = ''
  try {
    await createUser({
      username: form.username,
      display_name: form.display_name || null,
      password: form.password,
      role: form.role,
      is_active: form.is_active,
    })
    message.value = '用户创建成功'
    form.username = ''
    form.display_name = ''
    form.password = ''
    form.role = 'teacher'
    form.is_active = true
    await loadUsers()
  } catch {
    error.value = '用户创建失败，请确认当前账号为管理员，且密码满足复杂度要求（至少 8 位且含字母+数字）。'
  }
}

onMounted(loadUsers)
</script>
