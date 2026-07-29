# 智慧大棚教学系统 — 项目上下文

> 最后更新：2026-07-20
> 适用版本：v4.2（AI 教学助手 DeepSeek + ESP32 硬件模拟器 + MCP 桥接，API 122 端点）

---

## 1. 项目概述

本项目是一个面向**小学劳动课与科学课**的智慧大棚教学管理平台。核心特色是"教学闭环"：教师创建班级/小组 → 学生绑定设备节点 → 教师发布任务 → 学生提交作业 → 教师批阅打分。

### 系统角色

| 角色 | 使用者 | 访问方式 | 功能 |
|:--|:--|:--|:--|
| **管理员** | 学校信息中心 | Vue 管理后台（JWT 登录） | 用户管理、操作日志、所有教学功能 |
| **教师** | 劳动课/科学课任课老师 | Vue 管理后台（JWT 登录） | 班级/小组/任务/批阅/设备/规则/作物管理 |
| **学生** | 小学生 | Vue 学生端（JWT 登录） | 查看任务、提交作业、查看环境数据（含图表）、个人中心（头像/昵称/密码） |

### 架构图

```
┌─ 大棚现场 ──────────────────────────────────────────┐
│                                                      │
│  ESP32 设备节点 ──MQTT──┐                             │
│   ├─ 传感器组件（温湿度/光照/pH）                     │
│   └─ 执行器组件（风扇/水泵/补光灯）                   │
│                                                      │
│  ESP32-CAM 视觉节点 ──HTTP──┐  （设备 token 鉴权）    │
│   └─ 拍照上传 → 病虫害诊断（ResNet50 5 分类）        │
│                                                      │
│  ESP32-S3 小智 AI ──HTTP──┐  （设备 token 鉴权）      │
│   └─ MCP 工具调用（6 个工具：传感器/控制/作物/任务） │
│                                                      │
│  ESP32-S3 TFT 上位机 ──MQTT──┐  （MQTT 设备鉴权）    │
│   ├─ UART 接收下位机传感器数据 → TFT 显示 + MQTT 上报│
│   └─ MQTT 接收执行器控制 → UART 下行到下位机         │
│                         ▼                            │
└─────────────────── FastAPI 后端 :8001 ────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
               Mosquitto    MySQL     Vue 前端
               MQTT Broker  数据库    管理/学生后台 :5173
```

### 数据模型层级

```
管理员 ─┐
        ├─ 班级 (Classroom) ─ 小组 (Group) ─ 学生 (User.student)
教师 ─┘                      │                  │
                             ├─ 设备节点 (DeviceNode) ─ 组件 (Component)
                             │       │                    ├─ 风扇
                             │       │                    ├─ 水泵
                             │       │                    ├─ 补光灯
                             │       │                    └─ 传感器
                             │       └─ 传感器数据 (SensorData)
                             │
                             ├─ 设备令牌 (DeviceToken) ─ 绑定小组 + 节点
                             │       ├─ esp32（MQTT 传感器上报）
                             │       ├─ esp32cam（HTTP 病虫害诊断上传）
                             │       ├─ esp32s3（HTTP MCP 工具调用）
                             │       └─ esp32s3_monitor（MQTT 上位机：传感器上报 + 执行器控制）
                             │
                             ├─ 病虫害诊断 (PestDiagnosis) ─ esp32cam 上传
                             │       └─ ResNet50 5 分类（番茄/草莓 × 健康/病害）
                             │
                             └─ MCP 调用日志 (McpCallLog) ─ esp32s3 调用
                                     └─ 30 天自动清理（expires_at）

教师 ─ 课堂任务 (ClassTask) ─ 指定小组
                             └─ 学生提交 (TaskSubmission) ─ 教师批阅 (score 0-100, feedback)

教师 ─ 实验 (Experiment) ─ 班级
       ├─ 对照组/实验组 (ExperimentGroup) ─ 小组
       └─ 观察记录 (ExperimentObservation) ─ 学生
```

### WebSocket 实时推送

传感器数据、设备状态、组件控制事件通过 WebSocket 实时推送到前端，替代传统轮询。
- 端点：`/ws?token={jwt}`
- 事件类型：`sensor_data`、`component_status`、`device_status`、`pest_diagnosis`、`notification`
- 权限过滤：教师/管理员接收全部数据，学生仅接收自己小组节点的数据
- 心跳：客户端每 30 秒发送 `"ping"`，后端回复 `"pong"`

---

## 2. 技术栈

| 层 | 技术 | 说明 |
|:--|:--|:--|
| 后端框架 | FastAPI 0.115 | Python 异步 Web 框架 |
| 数据库 ORM | SQLAlchemy 2.0 | ORM + MySQL 8.0（pymysql 驱动，utf8mb4） |
| 认证 | JWT (python-jose) | OAuth2 Password Bearer（表单格式登录） |
| 密码哈希 | passlib + bcrypt (4.0.x) | 单向哈希存储，bcrypt 限制 72 字节 |
| MQTT | paho-mqtt 2.1 + Mosquitto | 设备通信 |
| 前端框架 | Vue 3 + Vite 5 + TypeScript | SPA 后台管理 |
| 状态管理 | Pinia | Vue 状态持久化 |
| 图表 | ECharts 5.5 | 传感器曲线 |
| 主题 | CSS Variables + useTheme composable | 深色/浅色主题切换 |

### 安全机制

- **密码复杂度**：至少 8 位且同时包含字母和数字
- **登录频率限制**：5 次失败后锁定 15 分钟（基于客户端 IP）
- **作业评分范围**：0-100（小学百分制）
- **头像上传限制**：最大 2MB，仅 jpg/png/webp 格式
- **学生修改密码**：需验证旧密码，新密码需满足复杂度要求

---

## 3. 项目结构

```
d:\IoT\
├── .env                          # 环境变量（含 MQTT 配置）
├── requirements.txt              # Python 依赖
├── simulate_hardware.py          # 硬件模拟器（ESP32 传感器/执行器模拟，MQTT 通信）
├── mcp_bridge.py                 # MCP 桥接器（连接小智 AI 官方后台）
├── README.md
├── CONTEXT.md
├── app/
│   ├── main.py                   # FastAPI 入口 + lifespan + 路由挂载
│   ├── core/
│   │   ├── config.py             # Pydantic Settings (含 MQTT 配置)
│   │   ├── dependencies.py       # get_db / get_current_user / require_roles
│   │   ├── logging.py            # 日志配置
│   │   ├── mqtt_client.py        # MQTT 客户端（lifespan 管理，自动重连，WebSocket 桥接）
│   │   ├── rate_limit.py         # 登录频率限制（内存字典，5 次失败后锁定 15 分钟）
│   │   ├── security.py           # JWT + bcrypt (含 72 字节截断保护)
│   │   └── websocket_manager.py  # WebSocket ConnectionManager（v4.0 新增，线程安全广播）
│   ├── db/
│   │   ├── base.py               # SQLAlchemy Base
│   │   └── session.py            # engine + SessionLocal
│   ├── models/                   # SQLAlchemy ORM 模型（21 个模型文件）
│   │   ├── enums.py              # UserRole/ComponentType/ComponentStatus/SensorMetric/
│   │   │                         RuleOperator/TaskStatus/CourseSubject/TaskType/ExperimentStatus/
│   │   │                         DeviceType/ExperimentRole/DiagnosisResult  # v4.1 新增 DeviceType/DiagnosisResult
│   │   ├── user.py               # 用户（含 display_name, avatar_url, group_id）
│   │   ├── device_node.py        # ESP32 设备节点
│   │   ├── component.py          # 组件（传感器/执行器）
│   │   ├── sensor_data.py        # 传感器数据（node_id, 含复合索引）
│   │   ├── rule.py               # 规则（action_component_type）
│   │   ├── rule_log.py           # 规则日志（node_id, component_id）
│   │   ├── device_log.py         # 设备日志（node_id, component_id）
│   │   ├── operation_log.py      # 操作审计日志
│   │   ├── crop.py               # 作物
│   │   ├── class_task.py         # 课堂任务（group_id, course_subject, task_type）
│   │   ├── classroom.py          # 班级
│   │   ├── group.py              # 小组（class_id, node_id）
│   │   ├── task_submission.py    # 学生提交（score, feedback, reviewed_at, reviewed_by）
│   │   ├── submission_file.py    # 提交附件（多文件，cascade delete-orphan）
│   │   ├── experiment.py         # 实验 + 实验组 + 观察记录（v4.0）
│   │   ├── courseware.py          # 课件模型（v3.4）
│   │   ├── teaching_resource.py   # 教学资源模型（v3.4）
│   │   ├── notification.py        # 通知模型（v4.1，P0-1 通知系统）
│   │   ├── device_token.py        # 设备鉴权令牌（v4.1，P0-NEW-0，esp32/esp32cam/esp32s3）
│   │   ├── pest_diagnosis.py      # 病虫害诊断（v4.1，P0-NEW-1，ESP32-CAM 上传）
│   │   └── mcp_call_log.py        # MCP 调用日志（v4.1，P0-NEW-2，ESP32-S3 小智 AI）
│   ├── schemas/                  # Pydantic 请求/响应模型（24 个 schema 文件）
│   │   ├── user.py, device_node.py, component.py, sensor_data.py, rule.py,
│   │   │   classroom.py, group.py, class_task.py, task_submission.py, crop.py,
│   │   │   dashboard.py, operation_log.py, device_log.py, rule_log.py, token.py,
│   │   │   student_analytics.py, courseware.py, teaching_resource.py,
│   │   │   experiment.py, submission_file.py, notification.py, device_token.py,
│   │   │   pest_diagnosis.py, mcp.py  # v4.1 新增 notification/device_token/pest_diagnosis/mcp
│   ├── routers/                  # API 端点（23 个路由文件，122 个端点）
│   │   ├── auth.py, users.py, device_nodes.py, sensors.py, rules.py,
│   │   │   classrooms.py, groups.py, tasks.py, submissions.py, student.py,
│   │   │   crops.py, logs.py, dashboard.py, analytics.py, courseware.py,
│   │   │   teaching_resources.py, experiments.py, notifications.py, exports.py,
│   │   │   device_tokens.py, pest_diagnoses.py, mcp.py, ws.py
│   ├── services/                 # 业务逻辑（21 个 service）
│   │   ├── user_service.py, device_node_service.py, sensor_service.py,
│   │   │   rule_service.py, classroom_service.py, group_service.py,
│   │   │   task_service.py, submission_service.py, student_service.py,
│   │   │   crop_service.py, log_service.py, dashboard_service.py,
│   │   │   student_analytics_service.py, courseware_service.py,
│   │   │   teaching_resource_service.py, experiment_service.py,
│   │   │   notification_service.py, export_service.py,
│   │   │   device_token_service.py, pest_diagnosis_service.py, mcp_service.py
│   └── scripts/
│       └── init_db.py            # 数据库建表 + 种子数据（main.py 启动时调用）
├── frontend/                     # Vue 3 前端
│   └── src/
│       ├── types.ts              # TypeScript 类型定义
│       ├── styles.css            # 全局样式 + 主题变量
│       ├── composables/
│       │   ├── useTheme.ts       # 主题切换 composable
│       │   └── useWebSocket.ts   # WebSocket 单例连接管理（模块级共享，自动重连/心跳）
│       ├── views/                # 管理端页面（19 个）
│       │   ├── LoginView, DashboardView, DevicesView, SensorsView, RulesView,
│       │   │   ClassroomsView, GroupsView, TasksView, GradingView,
│       │   │   CropsView, LogsView, UsersView
│       │   ├── StudentAnalyticsView, CoursewareView, ResourcesView  # v3.4 新增
│       │   ├── ClassroomDashboardView  # v4.1 班级驾驶舱（P0-2）
│       │   ├── ExperimentsView   # 实验管理（v4.0，含创建/详情/小组分配）
│       │   ├── PestDiagnosisView # 病虫害诊断（v4.1，P0-NEW-1）
│       │   ├── McpToolsView      # MCP 工具管理（v4.1，P0-NEW-2）
│       │   └── student/          # 学生端页面（8 个）
│       │       ├── StudentDashboardView, StudentTasksView,
│       │       │   StudentSensorView, StudentSubmissionsView, StudentProfileView,
│       │       │   StudentResourcesView, StudentExperimentsView,
│       │       │   StudentPestDiagnosisView  # v4.1 新增
│       ├── components/           # SectionCard, StatCard, LineChart, NotificationBell
│       ├── api/                  # 22 个模块（http.ts + 21 个资源 API）
│       │   ├── http.ts, auth.ts, users.ts, device_nodes.ts, sensors.ts, rules.ts,
│       │   │   classrooms.ts, groups.ts, tasks.ts, submissions.ts, student.ts,
│       │   │   crops.ts, logs.ts, dashboard.ts, analytics.ts, courseware.ts,
│       │   │   resources.ts, experiments.ts, notifications.ts, device_tokens.ts,
│       │   │   pest_diagnosis.ts, mcp.ts  # v4.1 新增
│       ├── stores/               # Pinia: auth.ts
│       ├── router/               # Vue Router（区分管理端/学生端）
│       └── layouts/              # AdminLayout, StudentLayout
├── scripts/
│   └── smoke_test_teacher.py     # 教师端 E2E 冒烟测试（19 项）
├── data/                         # 文件上传存储（数据库由 MySQL 管理）
│   ├── avatars/                  # 用户头像上传目录
│   ├── courseware/               # 课件文件（50MB 限制）
│   ├── resources/                # 教学资源文件
│   ├── submissions/              # 作业提交附件
│   └── pest-images/              # 病虫害诊断图片（ESP32-CAM 上传，v4.1 新增）
└── tests/                        # 测试套件（365 项，含设备鉴权+病虫害诊断+MCP+AI 助手）
    ├── conftest.py               # 测试 fixtures（含 student_token）
    ├── test_api.py               # API 集成测试
    ├── test_unit.py              # Schema/枚举单元测试
    └── test_e2e.py               # 端到端流程测试
```

---

## 4. 角色权限矩阵

> 以下权限以**后端路由 `require_roles` 实际校验**为准。

| 功能 | admin | teacher | student |
|:--|:--:|:--:|:--:|
| 用户管理（增删改查） | ✅ | ❌ | ❌ |
| 操作日志查看 | ✅ | ❌ | ❌ |
| 设备日志/规则日志查看 | ✅ | ✅ | ❌ |
| 设备节点管理（增删改） | ✅ | ✅ | ❌ |
| 设备节点列表/详情 | ✅ | ✅ | ❌ |
| 组件控制（开/关/自动） | ✅ | ✅ | ❌ |
| 传感器数据查看/上报 | ✅ | ✅ | ❌ |
| 自动规则（增删改/开关） | ✅ | ✅ | ❌ |
| 班级管理 | ✅ | ✅ | ❌ |
| 小组管理 | ✅ | ✅ | ❌ |
| 批量创建学生 | ✅ | ✅ | ❌ |
| 任务管理 | ✅ | ✅ | ❌ |
| 作业批阅 | ✅ | ✅ | ❌ |
| 作物管理 | ✅ | ✅ | ❌ |
| 仪表盘查看 | ✅ | ✅ | ❌ |
| 实验创建/管理 | ✅ | ✅ | ❌ |
| 实验小组分配 | ✅ | ✅ | ❌ |
| 观察记录查看/创建 | ✅ | ✅ | ✅ |
| 设备鉴权令牌管理 | ✅ | ✅ | ❌ |
| 病虫害诊断查看 | ✅ | ✅ | ✅（仅本组） |
| 病虫害诊断删除 | ✅ | ❌ | ❌ |
| MCP 工具调用 | — | — | —（设备 token） |
| MCP 调用日志查看 | ✅ | ✅ | ❌ |
| 通知查看 | ✅ | ✅ | ✅ |
| 学生成长档案 PDF 导出 | ✅ | ✅ | ❌ |
| 班级驾驶舱 | ✅ | ✅ | ❌ |
| 学生端 `/student/me/*` | — | — | ✅ |

---

## 5. API 端点一览

共 122 个端点，基础路径 `/api/v1`。创建类返回 201，删除类返回 204。设备 token 鉴权的端点使用 `Authorization: Bearer <device_token>` 头。

### 认证

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| POST | `/auth/login` | 登录（表单格式） | 公开 |
| GET | `/auth/me` | 获取当前用户 | 已登录 |

### 用户

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/users` | 用户列表 | admin |
| POST | `/users` | 创建用户 | admin |
| PATCH | `/users/{user_id}` | 更新用户 | admin |

### 设备节点与组件

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/device-nodes` | 节点列表（`online` 筛选） | 已登录 |
| POST | `/device-nodes` | 创建节点 | admin, teacher |
| GET | `/device-nodes/{node_id}` | 节点详情 | 已登录 |
| PATCH | `/device-nodes/{node_id}` | 更新节点 | admin, teacher |
| DELETE | `/device-nodes/{node_id}` | 删除节点（级联组件） | admin |
| GET | `/device-nodes/{node_id}/components` | 组件列表 | 已登录 |
| POST | `/device-nodes/{node_id}/components` | 添加组件 | admin, teacher |
| PATCH | `/device-nodes/{node_id}/components/{component_id}` | 更新组件 | admin, teacher |
| POST | `/device-nodes/{node_id}/components/{component_id}/control` | 控制组件 | admin, teacher |
| GET | `/device-nodes/{node_id}/logs` | 节点日志 | admin, teacher |

### 传感器数据

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| POST | `/sensors/data` | 上报数据（触发规则） | admin, teacher |
| GET | `/sensors/data` | 历史数据（`node_id`, `limit`） | admin, teacher |
| GET | `/sensors/data/latest` | 最新数据 | admin, teacher |
| GET | `/sensors/data/echarts` | ECharts 格式 | admin, teacher |

### 规则

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/rules` | 规则列表 | admin, teacher |
| POST | `/rules` | 创建规则 | admin, teacher |
| PATCH | `/rules/{rule_id}` | 更新规则 | admin, teacher |
| POST | `/rules/{rule_id}/toggle` | 启停规则 | admin, teacher |
| GET | `/rules/logs` | 规则日志 | admin, teacher |

### 班级

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/classrooms` | 班级列表（`teacher_id`, `subject`） | admin, teacher |
| POST | `/classrooms` | 创建班级 | admin, teacher |
| GET | `/classrooms/{classroom_id}` | 班级详情 | admin, teacher |
| PATCH | `/classrooms/{classroom_id}` | 更新班级 | admin, teacher |
| DELETE | `/classrooms/{classroom_id}` | 删除班级 | admin, teacher |

### 小组

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/groups` | 小组列表 | admin, teacher |
| POST | `/groups` | 创建小组（可绑定 node_id） | admin, teacher |
| GET | `/groups/{group_id}` | 小组详情 | admin, teacher |
| PATCH | `/groups/{group_id}` | 更新小组 | admin, teacher |
| DELETE | `/groups/{group_id}` | 删除小组 | admin, teacher |
| POST | `/groups/{group_id}/bind-node?node_id=X` | 绑定节点 | admin, teacher |
| POST | `/groups/{group_id}/unbind-node` | 解绑节点 | admin, teacher |
| GET | `/groups/{group_id}/students` | 学生名单 | admin, teacher, student |
| POST | `/groups/{group_id}/students/batch` | 批量创建学生 | admin, teacher |

### 课堂任务

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/tasks` | 任务列表（`group_id`） | admin, teacher |
| POST | `/tasks` | 创建任务 | admin, teacher |
| GET | `/tasks/{task_id}` | 任务详情 | admin, teacher |
| PATCH | `/tasks/{task_id}` | 更新任务 | admin, teacher |

### 作业提交与批阅

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/submissions` | 提交列表（`task_id`, `student_id`, `reviewed`） | admin, teacher |
| POST | `/submissions?task_id=X` | 学生提交（支持重交重置批阅） | student |
| GET | `/submissions/{submission_id}` | 提交详情 | 提交者或 admin/teacher |
| POST | `/submissions/{submission_id}/review` | 批阅（score 0-100 + feedback） | admin, teacher |

### 学生端

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/student/me/group` | 我的小组 | student |
| GET | `/student/me/tasks` | 我的任务 | student |
| GET | `/student/me/submissions` | 我的提交（`task_id`） | student |
| GET | `/student/me/sensor-data` | 我的传感器数据（`limit`） | student |
| GET | `/student/me/sensor-data/latest` | 我的最新数据 | student |
| GET | `/student/me/sensor-data/echarts` | ECharts 格式传感器数据（`metrics`, `limit`） | student |
| POST | `/student/me/tasks/{task_id}/submit` | 提交作业 | student |
| PATCH | `/student/me/profile` | 更新昵称/头像 URL | student |
| PATCH | `/student/me/password` | 修改密码（旧密码 + 新密码） | student |
| POST | `/student/me/avatar` | 上传头像文件（multipart，2MB，jpg/png/webp） | student |

### 静态资源

| 方法 | 路径 | 说明 |
|:--|:--|:--|
| GET | `/avatars/{filename}` | 用户头像文件（FastAPI StaticFiles 挂载） |
| GET | `/courseware-files/{filename}` | 课件文件 |
| GET | `/resource-files/{filename}` | 教学资源文件 |
| GET | `/submission-files/{filename}` | 作业提交附件 |
| GET | `/pest-images/{filename}` | 病虫害诊断图片（v4.1 新增） |

### 作物

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/crops` | 作物列表（`group_id`） | admin, teacher |
| POST | `/crops` | 创建作物 | admin, teacher |
| GET | `/crops/{crop_id}` | 作物详情 | admin, teacher |
| PATCH | `/crops/{crop_id}` | 更新作物 | admin, teacher |

### 日志

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/logs/operations` | 操作审计日志 | admin |
| GET | `/logs/device` | 设备日志（`node_id`, `component_id`） | admin, teacher |
| GET | `/logs/rules` | 规则日志 | admin, teacher |

### 仪表盘

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/dashboard/overview` | 概览（节点数/在线数/规则数/任务数/最新数据） | admin, teacher |
| GET | `/dashboard/component-summary` | 组件类型聚合 | admin, teacher |

### 通知（v4.1 P0-1）

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/notifications` | 通知列表（`unread_only` 筛选） | 已登录 |
| POST | `/notifications/{id}/read` | 标记已读 | 已登录 |
| POST | `/notifications/read-all` | 全部标记已读 | 已登录 |
| GET | `/notifications/unread-count` | 未读数量 | 已登录 |

### 学生分析 + 班级驾驶舱（v4.1 P0-2）

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/analytics/students/{id}` | 学生学习画像 | admin, teacher |
| GET | `/analytics/students/{id}/score-trend` | 成绩趋势 | admin, teacher |
| GET | `/analytics/classrooms/{id}/overview` | 班级驾驶舱（学情/小组排行/任务进度/评分分布） | admin, teacher |

### 学生成长档案 PDF 导出（v4.1 P0-3）

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/exports/students/{id}/growth-pdf` | 导出学生成长档案 PDF（reportlab，6 个章节） | admin, teacher |

### 设备鉴权令牌（v4.1 P0-NEW-0）

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/device-tokens` | 令牌列表（`group_id`, `device_type`, `is_active` 筛选） | admin, teacher |
| GET | `/device-tokens/me` | 设备自检（设备 token 鉴权） | 设备 token |
| POST | `/device-tokens` | 创建令牌（返回明文，仅此一次） | admin, teacher |
| POST | `/device-tokens/{id}/reset` | 重置令牌字符串 | admin, teacher |
| POST | `/device-tokens/{id}/revoke` | 吊销令牌 | admin, teacher |
| DELETE | `/device-tokens/{id}` | 硬删除令牌 | admin |

### 病虫害诊断（v4.1 P0-NEW-1）

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| POST | `/pest-diagnoses/upload` | ESP32-CAM 上传图片诊断（设备 token，仅 esp32cam） | 设备 token |
| GET | `/pest-diagnoses` | 诊断列表（`group_id`, `diagnosis_result` 筛选） | admin, teacher |
| GET | `/pest-diagnoses/{id}` | 诊断详情 | admin, teacher |
| DELETE | `/pest-diagnoses/{id}` | 删除诊断记录 + 图片文件 | admin |
| GET | `/student/me/pest-diagnoses` | 学生查看本组诊断 | student |

### MCP 工具（v4.1 P0-NEW-2）

| 方法 | 路径 | 说明 | 权限 |
|:--|:--|:--|:--|
| GET | `/mcp/tools` | MCP 工具清单（6 个工具定义） | 设备 token |
| POST | `/mcp/tools/call` | 调用 MCP 工具（自动 scope 到设备小组） | 设备 token |
| GET | `/mcp/logs` | MCP 调用日志（`group_id`, `tool_name` 筛选） | admin, teacher |

### 公开接口

| 方法 | 路径 | 说明 |
|:--|:--|:--|
| GET | `/health` | 健康检查（返回 status 和 mqtt 状态） |
| GET | `/avatars/{filename}` | 用户头像静态文件（无需认证） |

---

## 6. MQTT 主题

| 主题 | 方向 | 说明 |
|:--|:--|:--|
| `greenhouse/sensor/data` | ESP32 → 后端 | 传感器数据 JSON（含 `node_id`） |
| `greenhouse/device/status` | ESP32 → 后端 | 设备节点在线/状态 |
| `greenhouse/device/control` | 后端 → ESP32 | 控制指令（含 `node_id`, `component_id`） |

### 传感器上报 JSON 格式

```json
{
    "node_id": 1,
    "air_temp": 26.5,
    "air_humidity": 62.0,
    "soil_humidity": 48.0,
    "light_intensity": 420,
    "soil_ph": 6.5,
    "timestamp": "2026-07-09T10:30:00"
}
```

### 控制指令 JSON 格式

```json
{
    "node_id": 1,
    "component_id": 2,
    "action": "on",
    "message": "后台手动控制",
    "timestamp": "2026-07-09T10:30:00"
}
```

---

## 7. 环境变量 (.env)

```ini
PROJECT_NAME=Smart Greenhouse Admin API
API_V1_STR=/api/v1
DATABASE_URL=mysql+pymysql://root:你的密码@localhost:3306/greenhouse?charset=utf8mb4
JWT_SECRET_KEY=...          # 必填：修改为你自己的密钥
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=*              # 生产环境请限制为具体域名
LOG_LEVEL=INFO
AUTO_CREATE_DB=true
INIT_ADMIN_USERNAME=admin
INIT_ADMIN_PASSWORD=Admin123456  # 生产环境务必修改
INIT_SAMPLE_DATA=true
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_CLIENT_ID=greenhouse-backend
```

---

## 8. 核心模块交互逻辑

### 8.1 认证流程

```
客户端 → POST /auth/login (OAuth2 表单: username, password)
       → user_service.authenticate() → 查用户 + verify_password
       → 登录频率限制检查（5 次失败后锁定 15 分钟）
       → create_access_token(user_id) → JWT (sub=user_id, exp, iat)
       → 客户端存储 token → 后续请求 Authorization: Bearer <token>
       → get_current_user() → decode_access_token() → get_user_by_id()
```

### 8.2 传感器数据流

```
ESP32/模拟器 → MQTT: greenhouse/sensor/data (含 node_id)
            → mqtt_client._handle_sensor_data()
            → sensor_service.create_sensor_data()
              → 校验节点存在 → 写入 SensorData
              → rule_service.evaluate_rules()  (自动评估规则)
                → 遍历 enabled 规则 → 比较阈值 → 查找匹配组件
                → 批量更新组件状态，写入 DeviceOperationLog、RuleLog、OperationLog
                → publish_device_control() → MQTT: greenhouse/device/control
              → db.commit()
```

### 8.3 组件控制流

```
前端 → POST /device-nodes/{node_id}/components/{component_id}/control
     → device_node_service.control_component()
       → 更新 component.status
       → 写入 DeviceOperationLog + OperationLog
       → db.commit() + db.refresh()
       → publish_device_control() → MQTT: greenhouse/device/control
       → ESP32 订阅 greenhouse/device/control 收到指令并执行
```

### 8.4 教学闭环流程

```
教师创建班级 → 创建小组 → 绑定设备节点 → 批量创建学生（用户名 g{组号}s{序号}）
教师创建任务（指定小组） → 学生登录学生端
学生查看任务 → 提交作业（content + 多文件附件）→ 提交记录写入 task_submissions + submission_files
教师打开批阅中心 → 查看待批阅列表 → 打分（0-100）+ 评语 → reviewed_at/reviewed_by 更新
学生重交 → 重置 score/feedback/reviewed_at/reviewed_by 为 null（需教师重新批阅）
```

### 8.5 主题切换机制

```
用户点击切换按钮 → useTheme.toggle()
               → 更新 currentTheme ref
               → watch: document.documentElement.setAttribute('data-theme', theme)
               → watch: localStorage.setItem('greenhouse-theme', theme)
               → CSS 变量自动切换（:root / [data-theme="light"]）
               → LineChart watch(theme) → 重新渲染 ECharts
```

### 8.6 学生个人中心流程

```
头像上传：
  前端 → POST /student/me/avatar (multipart/form-data)
       → 校验 content_type ∈ {image/jpeg, image/png, image/webp}
       → 读取文件内容，校验 ≤ 2MB
       → 保存到 data/avatars/{user_id}_{timestamp}_{随机token}.{ext}
       → 更新 user.avatar_url = /avatars/{filename}
       → 返回 {"avatar_url": "/avatars/{filename}"}
  前端 → auth.updateProfile({ avatar_url }) → 全局同步头像

修改密码：
  前端校验（≥8 位 + 字母 + 数字 + 两次一致）
  → PATCH /student/me/password { old_password, new_password }
  → verify_password(old, hashed) → 失败返回 400
  → _validate_password_complexity(new) → 失败返回 422
  → get_password_hash(new) → 更新 user.hashed_password
  → 返回 UserOut

修改昵称：
  → PATCH /student/me/profile { display_name }
  → 更新 user.display_name
  → 前端 auth.updateProfile({ display_name }) → 全局同步
```

---

## 9. 关键算法说明

### 9.1 规则评估引擎

`rule_service.evaluate_rules()` 在每次传感器数据写入时自动调用：

1. 查询所有 `enabled=True` 的规则
2. 对每条规则，从传感器数据中读取对应 metric 值
3. 使用 `_compare()` 函数比较值与阈值（支持 `>`, `>=`, `<`, `<=`）
4. 若触发，查找节点下匹配 `action_component_type` 的所有组件
5. 批量更新组件状态，写入 DeviceOperationLog、RuleLog、OperationLog
6. 对每个被控制的组件调用 `publish_device_control()` 推送 MQTT 指令
7. 返回触发规则数量

### 9.2 学生用户名生成

`group_service.batch_create_students()` 批量创建学生账号：

1. 查询小组中已有学生数量 `existing_count`
2. 序号从 `existing_count + 1` 开始
3. 用户名格式：`g{group_id}s{seq}`（如 g1s1、g1s2、g2s1）
4. 密码统一设置（需满足复杂度：8+ 位且含字母+数字）
5. role 设为 `student`，group_id 设为当前小组

### 9.3 作业重交逻辑

`submission_service.create_submission()` 处理重交：

1. 查询该学生对该任务是否已有提交
2. 若已有：更新 content/submitted_at（新文件替换旧附件），重置 score/feedback/reviewed_at/reviewed_by 为 None
3. 若无：创建新提交记录

### 9.4 ECharts 数据构建

`sensor_service.build_echarts_data()` 将传感器数据转换为 ECharts 格式：

1. 接受 `rows` (SensorData 列表) 和 `metrics` (可选指标列表)
2. 按时间正序排列（`reversed(rows)`）
3. 为每个 metric 生成一个 series，提取对应字段值
4. 返回 `{ x: [时间戳], series: [{ name, data }] }`

---

## 10. 启动指南

### 10.1 后端

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 .env 文件（至少设置 JWT_SECRET_KEY）

# 3. 启动 MQTT Broker (Windows: 从 mosquitto.org 下载安装)
mosquitto -v

# 4. 启动后端（启动时自动建表和填充种子数据）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### 10.2 前端（管理后台 + 学生端）

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
```

### 10.3 运行测试

```bash
# 全部测试
python -m pytest tests/ -v

# 教师端 E2E 冒烟测试（需先启动后端）
python scripts/smoke_test_teacher.py
```

---

## 11. 默认账号

| 用户名 | 密码 | 角色 | 显示名 |
|:--|:--|:--|:--|
| `admin` | 见 `.env` 中 `INIT_ADMIN_PASSWORD` | 管理员 | - |
| `teacher` | `Teacher123456` | 教师 | 王老师 |
| `g1s1` | `Student123456` | 学生 | 张小明 |
| `g1s2` | `Student123456` | 学生 | 李小红 |
| `g2s1` | `Student123456` | 学生 | 王大力 |
| `g3s1` | `Student123456` | 学生 | 刘小华 |

> 种子数据包含 1 个班级（五(3)班，劳动课）、3 个小组（各绑定 1 个设备节点）、4 个学生账号、2 条规则、2 个作物、2 个任务、8 条传感器数据。
> 第 1 组额外种子 3 个设备令牌（固定值便于演示）：`esp32_g1_demo_token_seed_0001` / `esp32cam_g1_demo_token_seed_0001` / `esp32s3_g1_demo_token_seed_0001`
> 生产环境请务必修改默认密码。

---

## 12. 变更记录

### 12.0 v4.2 变更（AI 教学助手 + ESP32 硬件模拟器 + MCP 桥接）

#### AI 教学助手（DeepSeek API）
- ✅ 新增 `ChatSession` / `ChatMessage` / `AiQuotaUsage` 模型（用户隔离、级联删除）
- ✅ 新增 `ai_service` + `ai` 路由（6 端点：会话 CRUD + 流式对话 + 配额查询）
- ✅ 双模型切换：`deepseek-chat` / `deepseek-reasoner`（关键词规则匹配）
- ✅ SSE 流式输出（`POST /ai/chat`，`StreamingResponse(text/event-stream)`）
- ✅ 配额管理：每日 50 次，独立计数表，删除会话不重置；API 失败自动回退
- ✅ 空会话清理：API 未配置或配额超限时自动删除空会话
- ✅ 角色感知系统提示：学生（棚棚小助手，通俗语言 ≤300 字）/ 教师（教学助手，专业简洁 ≤500 字）
- ✅ 前端：`AiAssistant.vue`（悬浮按钮 + 右侧抽屉）+ `AiMessage.vue`（Markdown 渲染）+ `useAI.ts`
- ✅ 流式修复：`XMLHttpRequest` + `onprogress` + `processedLength` 独立跟踪（解决 ERR_ABORTED 和重复回答问题）
- ✅ 会话隔离：`ChatSession.user_id == current_user.id` 强制约束

#### ESP32 硬件模拟器
- ✅ 重写 `simulate_hardware.py`，适配 `DeviceNode` + `Component` 模型
- ✅ MQTT 通信：传感器上报、状态心跳、控制命令订阅
- ✅ 环境联动模型：风扇降温降湿、水泵增湿、补光灯增光
- ✅ 日间变化：6:00-14:00 渐升，夜间低温低光
- ✅ 自动加载数据库组件配置

#### MCP 桥接器
- ✅ 新增 `mcp_bridge.py`：连接小智 AI 官方后台 WebSocket（JSON-RPC 2.0）
- ✅ 标准 MCP 协议：`initialize` / `tools/list` / `tools/call`
- ✅ 自动转发到本地 API（`/api/v1/mcp/tools/call`，设备 token 鉴权）
- ✅ 指数退避重连（5s→60s）

#### 测试与文档
- ✅ 测试总数从 314 提升到 348（+34：AI 助手 34 项）
- ✅ API 端点数保持 122 不变（AI 新增 6 端点，无删除）
- ✅ CLAUDE.md / README.md / CONTEXT.md / CODE_WIKI.md 全面更新

### 12.1 v4.1 变更（IoT 硬件整合：设备鉴权 + ESP32-CAM + 小智 AI MCP）

#### P0-1 通知系统
- ✅ 新增 `Notification` 模型 + `notification_service` + `notifications` 路由（4 端点）
- ✅ WebSocket 推送 `notification` 事件
- ✅ 前端 `NotificationBell` 组件（AdminLayout + StudentLayout 顶栏）

#### P0-2 班级驾驶舱
- ✅ `GET /analytics/classrooms/{id}/overview` — 班级学情聚合（小组排行/任务进度/评分分布）
- ✅ 前端 `ClassroomDashboardView` + 路由 + 导航

#### P0-3 学生成长档案 PDF 导出
- ✅ 新增 `export_service` + `exports` 路由
- ✅ `GET /exports/students/{id}/growth-pdf` — reportlab 生成 6 章节 PDF（封面/概览/成绩趋势/提交频率/近期活动/教师评语）
- ✅ 中文字体 STSong-Light 支持

#### P0-NEW-0 设备鉴权基础设施
- ✅ 新增 `DeviceType` 枚举（esp32 / esp32cam / esp32s3）
- ✅ 新增 `DeviceToken` 模型 + `device_token_service` + `device_tokens` 路由（6 端点）
- ✅ 新增 `DeviceContext` + `get_device_context` 依赖（独立 HTTPBearer，与用户 JWT 共存）
- ✅ 数据隔离：token → group_id → 自动 scope
- ✅ Token 安全：明文仅创建/reset 时返回一次，不可部分匹配查询
- ✅ init_db 种子：第 1 组 3 个设备各一个固定 token

#### P0-NEW-1 ESP32-CAM 视觉节点（病虫害诊断）
- ✅ `DiagnosisResult` 枚举（5 分类：番茄/草莓 × 健康/早疫晚疫叶焦病）
- ✅ 新增 `PestDiagnosis` 模型 + `pest_diagnosis_service` + `pest_diagnoses` 路由（4 端点）
- ✅ ResNet50 真实推理：PyTorch 模型懒加载（`models/pest_model.pth`），自动 CUDA 检测
- ✅ 上传端点：`POST /pest-diagnoses/upload`（设备 token，仅 esp32cam）
- ✅ WebSocket 推送 `pest_diagnosis` 事件 + 教师通知
- ✅ 学生端 `GET /student/me/pest-diagnoses`（仅本组）
- ✅ 30 天自动清理（`cleanup_old_diagnoses`）
- ✅ 前端：PestDiagnosisView（管理端表格+图片预览+实时）+ StudentPestDiagnosisView（学生端卡片）

#### P0-NEW-2 小智 AI MCP 交互终端
- ✅ 新增 `McpCallLog` 模型（group_id + tool_name + arguments + result + duration_ms + expires_at 30 天）
- ✅ 新增 `mcp_service` + `mcp` 路由（3 端点）
- ✅ 6 个 MCP 工具（全部自动 scope 到 device.group_id）：
  - `get_latest_sensor_data` — 本组最新传感器数据
  - `control_components_by_type` — 按类型批量控制执行器（fan/pump/light × on/off/auto）
  - `get_group_components` — 本组执行器状态
  - `get_crop_status` — 本组作物信息
  - `list_pending_tasks` — 本组未完成任务
  - `list_group_rules` — 本组节点规则
- ✅ 安全设计：跨组隔离由设计保证（call_tool 强制使用 device.group_id）
- ✅ 前端：McpToolsView（工具清单 + 调用日志表 + 管理员在线试用）

#### 测试与文档
- ✅ 测试总数从 244 提升到 314（+70：设备鉴权 20 + 病虫害诊断 20 + MCP 21 + 其他 9）
- ✅ API 端点从 102 增至 122（+20：设备鉴权 6 + 病虫害 5 + MCP 3 + 通知 4 + 导出 1 + 班级驾驶舱 1）
- ✅ CONTEXT.md 全面更新

#### v4.1 审查修复（2026-07-15）
- ✅ F-1：AdminLayout roleAccess 补充 `classroom-dashboard`（原遗漏导致导航项不可见）
- ✅ F-2：AdminLayout + StudentLayout 顶栏渲染 `NotificationBell` 组件（原仅 import 未使用）
- ✅ F-3：useWebSocket.ts 添加 `notification` 事件处理，返回 `latestNotification` ref；两个 layout 监听该 ref 实时刷新铃铛未读数
- ✅ C-1：ClassroomDashboardView 班级选择器 `class="input"` → `class="select"`（与其他视图一致）
- ✅ C-2：McpToolsView 移除冗余 `tokenId` 选择框及 `onTokenSelect` 函数（原选择后无实际作用）
- ✅ D-1：路由文件数 22 → 23（含 ws.py）

#### v4.1 二次审查修复（2026-07-16）
- ✅ F-4：styles.css `.select` 浅色模式下拉箭头重复（`background` 简写覆盖 `background-image`/`background-repeat` 子属性）— 拆分公共选择器、改用 `background-color`、补全 `background-size` 和浏览器前缀
- ✅ F-5：NotificationBell/McpToolsView/StudentPestDiagnosisView/ClassroomDashboardView 使用未定义 CSS 变量（`--border`/`--surface`/`--surface-2`/`--text-muted`/`--primary-bg`/`--danger-bg`）— 统一替换为全局主题变量（`--line`/`--panel`/`--panel-hover`/`--muted`/`--primary-soft`/`--danger-soft`/`--bg-elevated`/`--shadow`）
- ✅ F-6：useWebSocket 非单例，每组件创建独立连接 — 重构为模块级单例，所有组件共享同一 WebSocket；登出时 `auth.logout()` 调用 `reset()` 断开并清理状态；数据加上限（component_status/device_status 各 50 条，pest_diagnosis 20 条）
- ✅ F-7：`experiments` 表缺少 `updated_at` 列导致 500 错误 — init_db.py 添加 `ALTER TABLE` 迁移逻辑（幂等，检查列是否存在后再添加）

### 12.1 v4.0 变更（实验管理 + WebSocket 实时推送）

#### 实验管理模块
- ✅ 实现 `Experiment` + `ExperimentGroup` + `ExperimentObservation` 的完整 CRUD
- ✅ 新增 `ExperimentRole` 枚举（control / experimental）
- ✅ `Experiment` 模型添加 `updated_at` 字段
- ✅ `ExperimentGroup.role` 从字符串改为枚举类型
- ✅ Schemas / Service / Router 全面实现（15 个 API 端点）
- ✅ 教师端实验管理页（创建/编辑/小组分配/观察记录查看）
- ✅ 学生端科学实验页（查看实验/记录观察/小组角色标识）
- ✅ 学生实验专用端点：`/student/me/experiments/*`（5 个端点）

#### WebSocket 实时推送
- ✅ 新增 `app/core/websocket_manager.py` — ConnectionManager 单例（线程安全广播）
- ✅ 新增 `app/routers/ws.py` — `/ws` WebSocket 端点（JWT 认证，角色过滤）
- ✅ 传感器数据广播（`sensor_service.create_sensor_data` → WebSocket）
- ✅ 组件状态广播（`rule_service.evaluate_rules` → WebSocket）
- ✅ 设备状态广播（`mqtt_client._handle_device_status` → WebSocket）
- ✅ 前端 `useWebSocket` composable（自动连接/指数退避重连/30 秒心跳）
- ✅ SensorsView/DevicesView/StudentSensorView 集成实时更新

#### 测试与文档
- ✅ 新增 6 项实验 schema 单元测试 + 13 项 API 测试 + 1 项 E2E 测试
- ✅ 新增 4 项 WebSocket 端点测试
- ✅ 测试总数从 219 提升到 244
- ✅ README / CONTEXT / CLAUDE 文档全面更新

### 12.3 v3.4 变更（教学平台基础功能）

#### 新增功能
- ✅ **学生画像**：教师查看学生行为分析（提交统计/成绩趋势/按时率），学生端个人中心增强统计
- ✅ **课件库**：教师上传课件（PPT/PDF/视频/文档），个人管理 + 公共分享市场（is_public 切换）
- ✅ **教学资源**：教师发布学习资料到班级/小组，学生端查看下载（独立于课件库）

#### 后端新增
- ✅ 新增 `courseware` 表（课件，含 is_public、owner_id、grade_level、tags）
- ✅ 新增 `teaching_resources` 表（教学资源，含 classroom_id/group_id/task_id、is_published、download_count）
- ✅ 新增 `student_analytics_service`（聚合查询，无需新表）
- ✅ 新增 3 个 router：`/analytics`（4 端点）、`/courseware`（7 端点）、`/resources`（7 端点）
- ✅ 新增 2 个 student 端点：`GET /student/me/analytics`、`GET /student/me/resources`
- ✅ StaticFiles 挂载：`/courseware-files`、`/resource-files`
- ✅ 文件存储：`data/courseware/`、`data/resources/`，50MB 限制
- ✅ API 端点总数：65 → 83

#### 前端新增
- ✅ 新增 4 个页面：`StudentAnalyticsView`、`CoursewareView`、`ResourcesView`、`StudentResourcesView`
- ✅ 新增 3 个 API 模块：`analytics.ts`、`courseware.ts`、`resources.ts`
- ✅ AdminLayout 新增 3 个导航项（学生画像/课件库/教学资源）
- ✅ StudentLayout 新增 1 个导航项（学习资源）
- ✅ `StudentProfileView` 学习统计增强（完成率/按时率）
- ✅ `types.ts` 新增 10 个 TypeScript 接口
- ✅ Vite 代理新增 `/courseware-files`、`/resource-files`
- ✅ CSS 新增 `.form-grid-span`、`.selected-row`

### 12.4 v3.3 变更（学生端扩充：图表 + 个人中心 + 响应式）

#### 后端新增
- ✅ User 模型新增 `avatar_url` 字段（VARCHAR(255)，nullable）
- ✅ 新增 `StudentProfileUpdate` / `StudentPasswordChange` Schema
- ✅ student_service 新增 3 个方法：`echarts_data_for_student`、`update_student_profile`、`change_student_password`
- ✅ student router 新增 4 个端点：`GET /me/sensor-data/echarts`、`PATCH /me/profile`、`PATCH /me/password`、`POST /me/avatar`
- ✅ FastAPI 挂载 `/avatars` StaticFiles 提供头像静态文件服务
- ✅ 头像上传限制：2MB、jpg/png/webp 三种格式
- ✅ 密码修改需验证旧密码 + 新密码满足复杂度（8+ 位且含字母+数字）

#### 前端新增
- ✅ 新建 `StudentProfileView.vue`（个人中心：头像上传 + 修改昵称 + 修改密码 + 学习统计）
- ✅ `StudentSensorView.vue` 接入 ECharts 折线图 + 6 项指标 chips 筛选器
- ✅ `StudentLayout.vue` 新增「个人中心」导航项 + topbar 头像快捷入口 + sidebar 头像显示
- ✅ `StudentDashboardView.vue` 顶部新增头像 + 个性化问候
- ✅ auth store 新增 `updateProfile` 方法，头像/昵称变更后全局同步
- ✅ `types.ts` User 接口新增 `avatar_url` 字段
- ✅ 响应式适配：`@media 760px`（sensor-grid 2 列、模态框全屏）+ `@media 480px`（1 列、紧凑布局）
- ✅ Vite 代理新增 `/avatars` 路径

#### 测试
- ✅ 测试套件从 206 项扩展到 219 项（新增 13 个学生端接口测试）

### 12.5 v3.2 变更（Phase 1：设备模型重构 + 教学层）

#### 设备模型重构
- ✅ 原 `Device` 模型拆分为 `DeviceNode`（ESP32 板）+ `Component`（传感器/执行器）
- ✅ `sensor_data.device_id` → `sensor_data.node_id`，新增 `(node_id, recorded_at)` 复合索引
- ✅ `rules.action_device_type` → `rules.action_component_type`
- ✅ `device_operation_logs.device_id` → `node_id` + `component_id`
- ✅ `rule_logs.device_id` → `node_id` + `component_id`
- ✅ 原 `/devices` 路由替换为 `/device-nodes`（含子资源 `/components`）
- ✅ Dashboard `total_devices/online_devices` → `total_nodes/online_nodes`
- ✅ Dashboard `device-summary` → `component-summary`

#### 教学层数据模型
- ✅ 新增 `classes`（班级）、`groups`（小组）、`task_submissions`（学生提交）表
- ✅ `users` 表新增 `display_name`、`group_id` 字段
- ✅ `class_tasks` 表新增 `group_id`、`course_subject`、`task_type` 字段
- ✅ 新增枚举：`CourseSubject`(labor/science)、`TaskType`(observation/experiment/maintenance)、`ExperimentStatus`(ongoing/completed)
- ✅ `UserRole` 新增 `student` 角色

#### 新增 API（v3.2 后共 61 个端点，v3.3 后共 65 个端点，v3.4 后共 83 个端点）
- ✅ 班级 CRUD：`/classrooms`
- ✅ 小组 CRUD + 绑定节点 + 批量创建学生：`/groups`
- ✅ 作业提交与批阅：`/submissions`
- ✅ 学生端专属接口：`/student/me/*`（v3.2: 6 个端点，v3.3: 10 个端点）

#### 新增前端页面
- ✅ 管理端：班级管理、小组概览、批阅中心
- ✅ 学生端：StudentLayout + StudentDashboardView + StudentTasksView + StudentSensorView + StudentSubmissionsView（v3.3 新增 StudentProfileView）
- ✅ DashboardView 重构为教学视角（班级概览、待批阅、最近任务）
- ✅ AdminLayout 导航重构为"主菜单/教学管理/系统管理"三组
- ✅ 路由守卫区分管理端/学生端，学生登录后跳转 `/student`

#### 安全与健壮性增强
- ✅ 密码复杂度验证（至少 8 位且含字母+数字）
- ✅ 登录频率限制（5 次失败后锁定 15 分钟）
- ✅ MQTT 自动重连配置
- ✅ 控制指令失败时返回状态并记录日志
- ✅ 健康检查接口返回 MQTT 连接状态
- ✅ `sensor_data` 表添加 `(node_id, recorded_at)` 复合索引
- ✅ `.gitignore` 保护敏感文件
- ✅ 作业评分范围统一为 0-100（小学百分制）

#### 测试
- ✅ 测试套件从原规模扩展到 206 项（含学生角色测试，v3.3 后 219 项）
- ✅ 新增教师端 E2E 冒烟测试脚本（`scripts/smoke_test_teacher.py`，19 项）

### 12.6 v3.0 变更（项目简化）

- ✅ 删除 `hardware/esp32s3_panel/` 目录（ESP32-S3 触屏面板固件）
- ✅ 删除 `templates/` 目录（Jinja2 公开展示页）
- ✅ 删除 `app/routers/display.py`、`display_page.py`、`app/schemas/display.py`
- ✅ `app/main.py` 移除 display 路由和 StaticFiles 挂载

### 12.5 v2.2 变更（第二轮代码审查修复）

- ✅ `device_service.control_device()` 提交后调用 `publish_device_control()`
- ✅ `rule_service.evaluate_rules()` 触发设备动作后下发 MQTT 指令
- ✅ 前端 401 拦截器调用 `auth.logout()` 清除状态
- ✅ `AdminLayout.vue` 导航按角色过滤

### 12.8 v2.1 变更（代码审查修复）

- ✅ `get_current_user()` 增加 JWT sub 解析异常处理
- ✅ `get_password_hash()` 增加 bcrypt 72 字节截断保护
- ✅ `requirements.txt` 锁定 `bcrypt>=4.0.0,<4.1.0`
- ✅ 前端深色/浅色主题切换功能

---

## 13. 待办与后续开发

### 已知遗留（已解决 ✅）

| 优先级 | 事项 | 说明 | 状态 |
|:--|:--|:--|:--:|
| 🟢 低 | 小智 AI 端适配文档 | 可选创建 `docs/xiaozhi-mcp-setup.md` 供 ESP32-S3 开发参考 | ⏳ |

### v4.1 IoT 硬件整合（大赛作品升级 — 已完成 🎉）

| 事项 | 状态 |
|:--|:--:|
| P0-1 通知系统 | ✅ 已实现 |
| P0-2 班级驾驶舱 | ✅ 已实现 |
| P0-3 学生成长档案 PDF | ✅ 已实现 |
| P0-NEW-0 设备鉴权基础设施 | ✅ 已实现 |
| P0-NEW-1 ESP32-CAM 病虫害诊断 | ✅ 已实现 |
| P0-NEW-2 小智 AI MCP 交互终端 | ✅ 已实现 |

### Phase 2 规划（科学课实验功能 — 全部已完成 🎉）

| 事项 | 状态 |
|:--|:--:|
| 2.1 实验模型 API | ✅ v4.0 已实现 |
| 2.2 实验配置页面 | ✅ v4.0 已实现 |
| 2.3 实验数据看板 | ✅ v4.0 已实现（基本版） |
| 2.4 学生端实验视图 | ✅ v4.0 已实现 |
| 2.5 实验模板库 | ⏳ 后续规划 |

### 其他建议

| 优先级 | 事项 | 说明 |
|:--|:--|:--|
| 🔴 高 | 生产环境安全加固 | 修改默认密码、限制 CORS 来源、启用 HTTPS |
| 🟡 中 | 传感器阈值告警前移 | 前端告警红色闪烁提示 |
| 🟢 低 | 数据库迁移到 PostgreSQL | 生产环境替换 MySQL（如需） |
