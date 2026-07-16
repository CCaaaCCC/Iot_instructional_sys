export type UserRole = 'admin' | 'teacher' | 'operator' | 'student'
export type ComponentType = 'fan' | 'pump' | 'light' | 'sensor'
export type ComponentStatus = 'on' | 'off' | 'auto'
export type RuleOperator = '>' | '>=' | '<' | '<='
export type SensorMetric = 'air_temp' | 'air_humidity' | 'soil_temp' | 'soil_humidity' | 'light_intensity' | 'soil_ph'
export type TaskStatus = 'pending' | 'in_progress' | 'done'
export type CourseSubject = 'labor' | 'science'
export type TaskType = 'observation' | 'experiment' | 'maintenance'
export type ExperimentStatus = 'ongoing' | 'completed'
export type ExperimentRole = 'control' | 'experimental'
export type DeviceType = 'esp32' | 'esp32cam' | 'esp32s3'
export type DiagnosisResult =
  | 'tomato_healthy'
  | 'tomato_early_blight'
  | 'tomato_late_blight'
  | 'cucumber_healthy'
  | 'cucumber_powdery_mildew'
  | 'cucumber_anthracnose'

export interface User {
  id: number
  username: string
  role: UserRole
  is_active: boolean
  display_name: string | null
  avatar_url: string | null
  group_id: number | null
  created_at: string
  updated_at: string
}

export interface DeviceNode {
  id: number
  name: string
  location: string | null
  online: boolean
  last_reported_at: string | null
  created_at: string
  updated_at: string
}

export interface Component {
  id: number
  node_id: number
  name: string
  type: ComponentType
  status: ComponentStatus
  metric: SensorMetric | null
  created_at: string
  updated_at: string
}

export interface SensorData {
  id: number
  node_id: number
  air_temp: number | null
  air_humidity: number | null
  soil_temp: number | null
  soil_humidity: number | null
  light_intensity: number | null
  soil_ph: number | null
  recorded_at: string
  created_at: string
}

export interface Rule {
  id: number
  name: string
  metric: SensorMetric
  operator: RuleOperator
  threshold: number
  action_component_type: ComponentType
  action: ComponentStatus
  enabled: boolean
  description: string | null
  created_at: string
  updated_at: string
}

export interface Crop {
  id: number
  name: string
  description: string | null
  growth_stage: string | null
  start_date: string | null
  end_date: string | null
  notes: string | null
  group_id: number | null
  created_at: string
  updated_at: string
}

export interface ClassTask {
  id: number
  title: string
  description: string | null
  assigned_date: string | null
  due_date: string | null
  status: TaskStatus
  created_by: number | null
  group_id: number | null
  course_subject: CourseSubject | null
  task_type: TaskType | null
  created_at: string
  updated_at: string
}

export interface Classroom {
  id: number
  name: string
  teacher_id: number | null
  subject: CourseSubject
  created_at: string
}

export interface Group {
  id: number
  name: string
  class_id: number
  node_id: number | null
  created_at: string
}

export interface SubmissionFile {
  id: number
  submission_id: number
  filename: string
  original_name: string
  file_url: string
  file_size: number
  file_type: string
  created_at: string
}

export interface TaskSubmission {
  id: number
  task_id: number
  student_id: number
  content: string | null
  submitted_at: string
  score: number | null
  feedback: string | null
  reviewed_at: string | null
  reviewed_by: number | null
  files: SubmissionFile[]
}

export interface OperationLog {
  id: number
  user_id: number | null
  action: string
  entity_type: string
  entity_id: string | null
  detail: string | null
  created_at: string
}

export interface DeviceOperationLog {
  id: number
  node_id: number | null
  component_id: number | null
  operator_id: number | null
  action: ComponentStatus
  message: string | null
  created_at: string
}

export interface RuleLog {
  id: number
  rule_id: number
  sensor_data_id: number | null
  node_id: number | null
  component_id: number | null
  message: string | null
  triggered_at: string
}

export interface DashboardOverview {
  total_nodes: number
  online_nodes: number
  total_rules: number
  enabled_rules: number
  total_tasks: number
  pending_tasks: number
  latest_sensor_data: SensorData | null
}

export interface ComponentSummaryItem {
  type: ComponentType
  total: number
  status_on: number
  status_off: number
  status_auto: number
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface EChartsSeries {
  name: string
  data: Array<number | null>
}

export interface EChartsResponse {
  x: string[]
  series: EChartsSeries[]
}

export interface BatchStudentCreate {
  group_id: number
  count: number
  password: string
  display_names?: string[]
}

// ---- Student Analytics ----
export interface StudentStats {
  student_id: number
  student_name: string
  total_submissions: number
  avg_score: number | null
  reviewed_count: number
  completed_tasks: number
  completion_rate: number
}

export interface StudentAnalyticsSummary {
  student_id: number
  student_name: string
  total_submissions: number
  avg_score: number | null
  total_tasks: number
  completed_tasks: number
  completion_rate: number
  on_time_count: number
  late_count: number
  on_time_ratio: number
}

export interface SubmissionTrendPoint {
  date: string
  count: number
}

export interface ScoreTrendPoint {
  date: string
  avg_score: number | null
}

export interface RecentActivity {
  type: string
  task_title: string | null
  date: string
  score: number | null
  detail: string | null
}

export interface StudentAnalyticsFull {
  summary: StudentAnalyticsSummary
  submission_frequency: SubmissionTrendPoint[]
  score_trend: ScoreTrendPoint[]
  recent_activity: RecentActivity[]
}

export interface StudentEChartsResponse {
  x: string[]
  series: Array<{ name: string; data: Array<number | null> }>
}

// ---- Classroom Dashboard ----
export interface GroupStat {
  group_id: number
  group_name: string
  student_count: number
  submission_count: number
  avg_score: number | null
  completion_rate: number
  pending_review_count: number
}

export interface TaskStat {
  task_id: number
  task_title: string
  task_type: string | null
  status: string
  due_date: string | null
  total_submissions: number
  unsubmitted_count: number
  avg_score: number | null
}

export interface ScoreDistribution {
  range_0_60: number
  range_60_70: number
  range_70_80: number
  range_80_90: number
  range_90_100: number
}

export interface ClassroomOverview {
  classroom_id: number
  classroom_name: string
  subject: string | null
  teacher_name: string | null
  total_students: number
  total_groups: number
  total_tasks: number
  avg_completion_rate: number
  avg_score: number | null
  pending_review_count: number
  on_time_ratio: number
  groups: GroupStat[]
  tasks: TaskStat[]
  score_distribution: ScoreDistribution
  echarts: {
    group_completion: StudentEChartsResponse
    score_distribution: StudentEChartsResponse
  }
}

// ---- Courseware ----
export interface Courseware {
  id: number
  title: string
  description: string | null
  file_type: string
  file_url: string
  preview_url: string | null
  file_size: number | null
  subject: string
  grade_level: string | null
  tags: string | null
  is_public: boolean
  owner_id: number
  owner_name?: string | null
  created_at: string
  updated_at: string
}

// ---- Teaching Resource ----
export interface TeachingResource {
  id: number
  title: string
  description: string | null
  resource_type: string
  file_url: string
  preview_url: string | null
  file_size: number | null
  subject: string
  classroom_id: number | null
  group_id: number | null
  task_id: number | null
  is_published: boolean
  publisher_id: number
  download_count: number
  created_at: string
  updated_at: string
}

// ---- Experiment ----
export interface Experiment {
  id: number
  class_id: number
  title: string
  hypothesis: string
  variable_metric: SensorMetric
  start_date: string
  end_date: string
  status: ExperimentStatus
  conclusion: string | null
  created_at: string
  updated_at: string
}

export interface ExperimentGroup {
  id: number
  experiment_id: number
  group_id: number
  role: ExperimentRole
  variable_target: string | null
  created_at: string
}

export interface ExperimentObservation {
  id: number
  experiment_id: number
  sensor_data_id: number | null
  student_id: number
  content: string | null
  recorded_at: string
}

// ---- Device Token ----
export interface DeviceToken {
  id: number
  group_id: number
  device_type: DeviceType
  device_name: string
  node_id: number
  is_active: boolean
  last_used_at: string | null
  created_at: string
  updated_at: string
}

export interface DeviceTokenWithSecret extends DeviceToken {
  token: string
}

export interface DeviceTokenListItem extends DeviceToken {
  group_name: string | null
  node_name: string | null
}

// ---- Pest Diagnosis ----
export interface PestDiagnosis {
  id: number
  group_id: number
  node_id: number
  device_token_id: number
  image_url: string
  diagnosis_result: DiagnosisResult
  confidence: number
  suggestion: string | null
  created_at: string
}

export interface PestDiagnosisListItem extends PestDiagnosis {
  group_name: string | null
  node_name: string | null
}

// ---- MCP 小智 AI ----
export interface McpToolParameter {
  type: string
  description: string
  enum?: string[]
  default?: unknown
}

export interface McpToolDefinition {
  name: string
  description: string
  parameters: Record<string, McpToolParameter>
}

export interface McpToolCallResponse {
  success: boolean
  result: Record<string, unknown> | null
  error: string | null
  duration_ms: number
}

export interface McpCallLog {
  id: number
  group_id: number
  device_token_id: number
  tool_name: string
  arguments: string | null
  result: string | null
  duration_ms: number
  success: boolean
  error_message: string | null
  created_at: string
  expires_at: string
}

export interface McpCallLogListItem extends McpCallLog {
  group_name: string | null
}
