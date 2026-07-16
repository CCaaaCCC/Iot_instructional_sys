import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import DevicesView from '../views/DevicesView.vue'
import SensorsView from '../views/SensorsView.vue'
import RulesView from '../views/RulesView.vue'
import LogsView from '../views/LogsView.vue'
import UsersView from '../views/UsersView.vue'
import CropsView from '../views/CropsView.vue'
import TasksView from '../views/TasksView.vue'
import ClassroomsView from '../views/ClassroomsView.vue'
import GroupsView from '../views/GroupsView.vue'
import GradingView from '../views/GradingView.vue'
import StudentAnalyticsView from '../views/StudentAnalyticsView.vue'
import ClassroomDashboardView from '../views/ClassroomDashboardView.vue'
import CoursewareView from '../views/CoursewareView.vue'
import ResourcesView from '../views/ResourcesView.vue'
import ExperimentsView from '../views/ExperimentsView.vue'
import PestDiagnosisView from '../views/PestDiagnosisView.vue'
import McpToolsView from '../views/McpToolsView.vue'
import AdminLayout from '../layouts/AdminLayout.vue'
import StudentLayout from '../layouts/StudentLayout.vue'
import StudentDashboardView from '../views/student/StudentDashboardView.vue'
import StudentTasksView from '../views/student/StudentTasksView.vue'
import StudentSensorView from '../views/student/StudentSensorView.vue'
import StudentSubmissionsView from '../views/student/StudentSubmissionsView.vue'
import StudentProfileView from '../views/student/StudentProfileView.vue'
import StudentResourcesView from '../views/student/StudentResourcesView.vue'
import StudentExperimentsView from '../views/student/StudentExperimentsView.vue'
import StudentPestDiagnosisView from '../views/student/StudentPestDiagnosisView.vue'

const roleAccess: Record<string, string[]> = {
  dashboard: ['admin', 'teacher'],
  devices: ['admin', 'teacher', 'operator'],
  sensors: ['admin', 'teacher'],
  rules: ['admin', 'teacher'],
  logs: ['admin', 'teacher'],
  users: ['admin'],
  crops: ['admin', 'teacher'],
  tasks: ['admin', 'teacher'],
  classrooms: ['admin', 'teacher'],
  groups: ['admin', 'teacher'],
  grading: ['admin', 'teacher'],
  analytics: ['admin', 'teacher'],
  'classroom-dashboard': ['admin', 'teacher'],
  courseware: ['admin', 'teacher'],
  resources: ['admin', 'teacher'],
  experiments: ['admin', 'teacher'],
  'pest-diagnoses': ['admin', 'teacher', 'operator'],
  'mcp-tools': ['admin', 'teacher', 'operator'],
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true },
    },
    {
      path: '/student',
      component: StudentLayout,
      meta: { requiresAuth: true },
      children: [
        { path: '', name: 'student-dashboard', component: StudentDashboardView },
        { path: 'tasks', name: 'student-tasks', component: StudentTasksView },
        { path: 'sensor', name: 'student-sensor', component: StudentSensorView },
        { path: 'submissions', name: 'student-submissions', component: StudentSubmissionsView },
        { path: 'resources', name: 'student-resources', component: StudentResourcesView },
        { path: 'experiments', name: 'student-experiments', component: StudentExperimentsView },
        { path: 'pest-diagnoses', name: 'student-pest-diagnoses', component: StudentPestDiagnosisView },
        { path: 'profile', name: 'student-profile', component: StudentProfileView },
      ],
    },
    {
      path: '/',
      component: AdminLayout,
      meta: { requiresAuth: true },
      children: [
        { path: '', name: 'dashboard', component: DashboardView },
        { path: 'devices', name: 'devices', component: DevicesView },
        { path: 'sensors', name: 'sensors', component: SensorsView },
        { path: 'rules', name: 'rules', component: RulesView },
        { path: 'logs', name: 'logs', component: LogsView },
        { path: 'users', name: 'users', component: UsersView },
        { path: 'crops', name: 'crops', component: CropsView },
        { path: 'tasks', name: 'tasks', component: TasksView },
        { path: 'classrooms', name: 'classrooms', component: ClassroomsView },
        { path: 'groups', name: 'groups', component: GroupsView },
        { path: 'grading', name: 'grading', component: GradingView },
        { path: 'analytics', name: 'analytics', component: StudentAnalyticsView },
        { path: 'classroom-dashboard', name: 'classroom-dashboard', component: ClassroomDashboardView },
        { path: 'courseware', name: 'courseware', component: CoursewareView },
        { path: 'resources', name: 'resources', component: ResourcesView },
        { path: 'experiments', name: 'experiments', component: ExperimentsView },
        { path: 'pest-diagnoses', name: 'pest-diagnoses', component: PestDiagnosisView },
        { path: 'mcp-tools', name: 'mcp-tools', component: McpToolsView },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      redirect: '/login',
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.isReady) {
    await auth.syncMe()
  }
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    const role = auth.user?.role
    if (role === 'student') return { name: 'student-dashboard' }
    return { name: role === 'operator' ? 'devices' : 'dashboard' }
  }
  // 学生角色只能访问 /student/* 路由
  if (auth.user?.role === 'student') {
    if (!to.path.startsWith('/student')) {
      return { name: 'student-dashboard' }
    }
  }
  // 非学生角色不能访问 /student 路由
  if (to.path.startsWith('/student') && auth.user?.role !== 'student') {
    return { name: 'dashboard' }
  }
  // 管理端路由按角色权限拦截
  const routeName = to.name as string
  if (roleAccess[routeName]) {
    const allowed = roleAccess[routeName]
    const role = auth.user?.role ?? ''
    if (!allowed.includes(role)) {
      return role === 'operator' ? { name: 'devices' } : { name: 'dashboard' }
    }
  }
})

export default router
