# 智慧大棚教学系统 · Code Wiki

> 面向小学劳动课 / 科学课的 IoT 智慧大棚教学管理平台。本 Wiki 从源码视角系统梳理项目整体架构、模块职责、关键类与函数、依赖关系及运行方式，作为开发与维护的代码索引文档。
>
> - **代码版本**：v4.2
> - **API 端点数**：122
> - **测试**：365 项（单元 + API 集成 + E2E）

---

## 目录

1. [项目概述](#1-项目概述)
2. [整体架构](#2-整体架构)
3. [目录结构总览](#3-目录结构总览)
4. [后端模块详解](#4-后端模块详解)
   - 4.1 [入口与生命周期 (`app/main.py`)](#41-入口与生命周期-appmainpy)
   - 4.2 [核心层 (`app/core/`)](#42-核心层-appcore)
   - 4.3 [数据库层 (`app/db/`)](#43-数据库层-appdb)
   - 4.4 [数据模型层 (`app/models/`)](#44-数据模型层-appmodels)
   - 4.5 [Schema 层 (`app/schemas/`)](#45-schema-层-appschemas)
   - 4.6 [业务逻辑层 (`app/services/`)](#46-业务逻辑层-appservices)
   - 4.7 [路由层 (`app/routers/`)](#47-路由层-approuters)
   - 4.8 [脚本 (`app/scripts/`)](#48-脚本-appscripts)
5. [前端模块详解](#5-前端模块详解)
   - 5.1 [入口与构建](#51-入口与构建)
   - 5.2 [API 层 (`src/api/`)](#52-api-层-srcapi)
   - 5.3 [状态管理 (`src/stores/`)](#53-状态管理-srcstores)
   - 5.4 [路由与守卫 (`src/router/`)](#54-路由与守卫-srcrouter)
   - 5.5 [布局与视图 (`src/layouts/` · `src/views/`)](#55-布局与视图-srclayouts--srcviews)
   - 5.6 [通用组件与组合式函数](#56-通用组件与组合式函数)
6. [关键类与函数索引](#6-关键类与函数索引)
7. [依赖关系](#7-依赖关系)
8. [认证与权限体系](#8-认证与权限体系)
9. [实时通信机制](#9-实时通信机制)
10. [项目运行方式](#10-项目运行方式)
11. [测试体系](#11-测试体系)

---

## 1. 项目概述

**智慧大棚教学系统**是一个贯穿"设备接入 → 数据采集 → 自动控制 → 教学管理 → 学情分析"完整闭环的物联网教学平台。它把真实的大棚硬件（ESP32 传感器节点、ESP32-CAM 视觉节点、ESP32-S3 小智 AI 语音节点）与课堂教学（班级 / 小组 / 任务 / 作业批阅 / 实验管理）打通，让小学生通过实体设备观察并记录植物生长过程。

### 核心能力

| 维度 | 能力 |
|------|------|
| 设备接入 | ESP32 经 MQTT 上报传感器数据；ESP32-CAM 经 HTTP（设备 token）上传图片做病虫害诊断；ESP32-S3 经 MCP 协议调用 6 个工具；ESP32-S3 Monitor（TFT 上位机）经 MQTT 上报传感器数据 + 接收执行器控制命令，通过 UART 与下位机通信 |
| 自动控制 | 规则引擎（温度 > 30℃ 自动开风扇等）在数据入库时评估并下发 MQTT 控制指令 |
| 教学闭环 | 班级 → 小组 → 学生 → 任务 → 作业提交（多附件）→ 教师批阅（0-100 分 + 评语）→ 学情分析 + PDF 成长档案 |
| 实时推送 | WebSocket 推送传感器数据、组件状态、设备上下线、病虫害诊断、通知 5 类事件，学生只收本组数据 |
| 角色权限 | admin / teacher / student 三角色，路由级 `require_roles` + 前端 `roleAccess` 双重控制 |

### 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | 0.115 |
| ORM | SQLAlchemy 2.0（Mapped 声明式） | 2.0.32 |
| 数据校验 | Pydantic v2 / pydantic-settings | 2.8.2 / 2.4.0 |
| 认证 | JWT（python-jose）+ bcrypt（passlib） | 3.3.0 / 1.7.4 |
| MQTT | paho-mqtt + Mosquitto | 2.1.0 |
| 数据库 | MySQL 8.0（pymysql 驱动，utf8mb4 字符集） | 8.0 |
| PDF 导出 | reportlab | ≥4.0.0 |
| 前端 | Vue 3（组合式 API）+ TypeScript | 3.5 |
| 构建 | Vite | 5.4 |
| 状态 | Pinia | 2.2 |
| 图表 | ECharts | 5.5 |

---

## 2. 整体架构

### 2.1 系统拓扑

```
┌─ 大棚现场 ──────────────────────────────────────────────────────┐
│  ESP32 传感器节点 ──MQTT──┐   (paho-mqtt, 3 主题)                │
│   ├─ 传感器组件                                                │
│   └─ 执行器（风扇 / 水泵 / 补光灯）                            │
│  ESP32-CAM 视觉节点 ──HTTP──┐  (设备 token 鉴权, 病虫害诊断)    │
│  ESP32-S3 小智 AI ──HTTP──┐    (设备 token 鉴权, MCP 6 工具)     │
│  ESP32-S3 TFT 上位机 ──MQTT──┐  (MQTT 设备鉴权, 传感器上报+执行器控制) │
│   ├─ UART 接收下位机传感器数据 → TFT 显示 + MQTT 上报云端       │
│   └─ MQTT 接收执行器控制命令 → UART 下行到下位机执行            │
└────────────────── FastAPI 后端 :8001 ────────────────────────────┘
                          │
            ┌─────────────┼──────────────┐
            ▼             ▼              ▼
       Mosquitto      MySQL         Vue 前端 :5173
       MQTT Broker    utf8mb4        (Vite 代理 /api → 8001)
                                      WebSocket /ws?token=jwt
```

### 2.2 后端分层架构

后端采用经典的 **四层架构**，每层职责单一、依赖单向向下：

```
┌──────────────────────────────────────────────────────────────┐
│  Routers 层 (app/routers/*.py)                               │
│  HTTP 端点定义、参数解析、依赖注入编排、HTTP 状态码            │
│  依赖 → Dependencies (get_db / require_roles / get_device_)  │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  Services 层 (app/services/*.py)                              │
│  业务逻辑：CRUD、规则评估、通知、PDF 生成、MCP 工具分发        │
│  调用 → Models + MQTT + WebSocket                             │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  Models 层 (app/models/*.py)   Schemas 层 (app/schemas/*.py)  │
│  SQLAlchemy ORM 实体            Pydantic 请求/响应模型         │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  Core 层 (app/core/*.py) + DB 层 (app/db/*.py)                │
│  配置 / 安全 / 依赖注入 / MQTT / WebSocket / 限流 / engine    │
└──────────────────────────────────────────────────────────────┘
```

### 2.3 核心请求流（传感器数据上报 → 规则触发 → 实时推送）

```
ESP32 ──MQTT publish──► Mosquitto ──► _on_message ──► _handle_sensor_data
                                                        │
                                          sensor_service.create_sensor_data
                                          ├─ 入库 SensorData
                                          ├─ 更新 DeviceNode.online/last_reported_at
                                          ├─ rule_service.evaluate_rules
                                          │   └─ 命中 → control_component
                                          │            ├─ 更新 Component.status
                                          │            ├─ 写 DeviceOperationLog + RuleLog
                                          │            └─ mqtt.publish_component_control ──► ESP32
                                          └─ ws_manager.broadcast_sync("sensor_data", ...)
                                                       │
                                                       ▼
                                          前端 useWebSocket.onmessage
                                          (学生只收本组 node_id 数据)
```

---

## 3. 目录结构总览

```
IoT/
├── app/                          # 后端应用
│   ├── core/                     # 核心模块（配置/安全/依赖/MQTT/WS/限流/日志/设备鉴权）
│   ├── db/                       # 数据库层（base 基类 + session engine）
│   ├── models/                   # ORM 数据模型（24 个实体，含 AI 对话和配额）
│   ├── schemas/                  # Pydantic 请求/响应模型（24 个）
│   ├── routers/                  # API 路由（23 个路由文件，122 端点）
│   ├── services/                 # 业务逻辑层（22 个 service）
│   ├── scripts/init_db.py        # 建表 + 种子数据 + 幂等迁移
│   └── main.py                   # FastAPI 入口（lifespan + 路由挂载 + 静态文件）
├── frontend/                     # 前端应用（Vue 3 + TS + Vite）
│   └── src/
│       ├── api/                  # HTTP 请求封装（23 个模块）
│       ├── components/           # 通用组件（StatCard/SectionCard/LineChart/NotificationBell/AiAssistant/AiMessage）
│       ├── composables/          # 组合式函数（useTheme/useWebSocket/useAI）
│       ├── layouts/              # 布局（AdminLayout/StudentLayout）
│       ├── router/index.ts       # 路由配置与导航守卫
│       ├── stores/auth.ts        # Pinia 认证状态
│       └── views/                # 页面（管理端 19 + 学生端 8）
├── scripts/smoke_test_teacher.py # 教师 E2E 冒烟测试
├── tests/                        # 测试套件（365 项）
├── data/                         # 数据目录（DB + avatars/courseware/resources/submissions/pest-images）
├── requirements.txt              # Python 依赖
├── .env / .env.example           # 环境变量
├── simulate_hardware.py          # 硬件模拟脚本（ESP32 传感器/执行器模拟，MQTT 通信）
└── mcp_bridge.py                 # MCP 桥接器（连接小智 AI 官方后台）
```

---

## 4. 后端模块详解

### 4.1 入口与生命周期 ([`app/main.py`](file:///d:/IoT/app/main.py))

`app/main.py` 是 FastAPI 应用入口，承担三件事：

- **生命周期管理（`lifespan`）**：启动时按 `AUTO_CREATE_DB` 调用 `init_db()` 建表 + 种子；启动 MQTT 客户端；向 `ws_manager` 注入主事件循环；关闭时停止 MQTT。
- **路由注册**：将 23 个 router 以 `settings.API_V1_STR`（`/api/v1`）为前缀挂载；`ws.router` 不带前缀。
- **静态文件挂载**：5 个 `StaticFiles` 目录（avatars / courseware-files / resource-files / submission-files / pest-images）。
- **CORS 中间件**：按 `CORS_ORIGINS` 配置，`*` 时禁用 `allow_credentials`。
- **健康检查**：`GET /health`（无前缀），返回 MQTT 连接状态。

### 4.2 核心层 (`app/core/`)

| 文件 | 职责 | 关键导出 |
|------|------|----------|
| [config.py](file:///d:/IoT/app/core/config.py) | pydantic-settings 读取 `.env` | `settings` 单例（含 DB / JWT / MQTT 配置） |
| [security.py](file:///d:/IoT/app/core/security.py) | JWT 签发/校验 + bcrypt 密码 | `create_access_token` / `decode_access_token` / `verify_password` / `get_password_hash` |
| [dependencies.py](file:///d:/IoT/app/core/dependencies.py) | FastAPI 依赖注入 | `get_db` / `get_current_user` / `require_roles(*roles)` |
| [device_auth.py](file:///d:/IoT/app/core/device_auth.py) | 设备 token 鉴权（与用户 JWT 独立） | `DeviceContext` / `get_device_context` |
| [mqtt_client.py](file:///d:/IoT/app/core/mqtt_client.py) | MQTT 客户端（订阅/发布/重连） | `start_mqtt` / `stop_mqtt` / `publish_component_control` |
| [websocket_manager.py](file:///d:/IoT/app/core/websocket_manager.py) | WebSocket 连接池与广播 | `ws_manager` 单例（`ConnectionManager`） |
| [rate_limit.py](file:///d:/IoT/app/core/rate_limit.py) | 登录频率限制 | 内存字典，5 次失败锁定 15 分钟 |
| [logging.py](file:///d:/IoT/app/core/logging.py) | 日志配置 | `setup_logging` |

#### 关键函数说明

**`security.py`**
- `get_password_hash(password)` — bcrypt 哈希，对密码做 `[:72]` 截断以规避 bcrypt 72 字节限制。
- `create_access_token(subject, expires_delta=None)` — 生成 JWT，payload 含 `sub`/`exp`/`iat`，有效期默认 1440 分钟。

**`dependencies.py`**
- `get_db()` — yield 一个 `SessionLocal`，请求结束自动关闭。
- `get_current_user(token)` — 解码 JWT 取 `sub` → 查用户 → 校验 `is_active`，失败抛 401。
- `require_roles(*roles)` — 返回闭包依赖，角色不匹配抛 403；路由级权限控制核心。

**`device_auth.py`**（v4.1 设备鉴权基础设施）
- `DeviceContext` — 数据类，含 `token / group_id / node_id / device_type`，业务层据此做数据隔离。
- `get_device_context(credentials)` — 校验 `Authorization: Bearer <device_token>`，返回 `DeviceContext`；与 `require_roles` 二选一，用于 ESP32-CAM / ESP32-S3 调用。

### 4.3 数据库层 (`app/db/`)

| 文件 | 职责 |
|------|------|
| [base.py](file:///d:/IoT/app/db/base.py) | `Base = declarative_base()`，所有模型的统一基类 |
| [session.py](file:///d:/IoT/app/db/session.py) | 模块级 `engine` + `SessionLocal`；MySQL 连接池（`pool_pre_ping=True` + `pool_recycle=3600`） |

- `engine` 配置 `pool_pre_ping=True`（连接前探活）+ `pool_recycle=3600`（每小时回收连接，避免 MySQL `wait_timeout` 断开）+ `future=True`（SQLAlchemy 2.0 风格）。
- MySQL InnoDB 引擎默认启用外键约束，无需额外 PRAGMA。
- 测试环境（`tests/conftest.py`）仍使用 SQLite 内存数据库，与生产环境隔离。

### 4.4 数据模型层 (`app/models/`)

所有模型继承 `Base`，使用 SQLAlchemy 2.0 `Mapped` 声明式。模型在 [`app/models/__init__.py`](file:///d:/IoT/app/models/__init__.py) 统一导出。

#### 枚举定义（[enums.py](file:///d:/IoT/app/models/enums.py)）

| 枚举 | 值 |
|------|------|
| `UserRole` | admin / teacher / student |
| `ComponentType` | sensor / fan / pump / light |
| `ComponentStatus` | on / off / auto |
| `RuleOperator` | `>` / `>=` / `<` / `<=` |
| `SensorMetric` | air_temp / air_humidity / soil_humidity / light_intensity / soil_ph / co2 |
| `TaskStatus` | pending / in_progress / done |
| `CourseSubject` | labor / science |
| `TaskType` | observation / experiment / maintenance |
| `ExperimentStatus` | ongoing / completed |
| `ExperimentRole` | control / experimental |
| `DeviceType` | esp32 / esp32cam / esp32s3 / esp32s3_monitor |
| `DiagnosisResult` | 5 类（番茄健康/早疫/晚疫，草莓健康/叶焦病） |

#### 实体模型清单（24 个）

| 模型 | 表名 | 关键字段 | 说明 |
|------|------|----------|------|
| `User` | users | username(唯一)、hashed_password、role、is_active、display_name、avatar_url、group_id(FK groups) | 用户账号（含学生，group_id 关联小组） |
| `DeviceNode` | device_nodes | name(唯一)、location、online、last_reported_at | ESP32 设备节点 |
| `Component` | components | node_id(FK)、name、type、status、metric | 节点下组件（执行器/传感器） |
| `SensorData` | sensor_data | node_id(FK)、6 项指标、recorded_at | 传感器数据，含 `(node_id, recorded_at)` 复合索引 |
| `Rule` | rules | name(唯一)、metric、operator、threshold、action_component_type、action、enabled | 自动控制规则 |
| `RuleLog` | rule_logs | rule_id、sensor_data_id、node_id、component_id、message、triggered_at | 规则触发日志 |
| `DeviceOperationLog` | device_operation_logs | node_id、component_id、operator_id、action、message | 设备操作日志 |
| `OperationLog` | operation_logs | user_id、action、entity_type、entity_id、detail | 操作审计日志 |
| `Classroom` | classes | name、teacher_id(FK)、subject | 班级 |
| `Group` | groups | name、class_id(FK)、node_id(FK) | 小组（绑定设备节点） |
| `ClassTask` | class_tasks | title、description、assigned_date、due_date、status、created_by、group_id、course_subject、task_type | 课堂任务 |
| `TaskSubmission` | task_submissions | task_id、student_id、content、submitted_at、score、feedback、reviewed_at、reviewed_by | 学生提交与批阅 |
| `SubmissionFile` | submission_files | submission_id(FK)、filename、original_name、file_url、file_size、file_type | 提交附件（一对多，级联删除） |
| `Crop` | crops | name(唯一)、description、growth_stage、start_date、end_date、notes、group_id | 作物档案 |
| `Courseware` | courseware | title、file_type、file_url、file_size、subject、grade_level、tags、is_public、owner_id | 课件（个人库 + 公共分享） |
| `TeachingResource` | teaching_resources | title、resource_type、file_url、subject、classroom_id、group_id、task_id、is_published、publisher_id、download_count | 教学资源分发 |
| `Experiment` | experiments | class_id、title、hypothesis、variable_metric、start_date、end_date、status、conclusion | 科学实验 |
| `ExperimentGroup` | experiment_groups | experiment_id、group_id、role、variable_target | 实验分组（对照/实验组） |
| `ExperimentObservation` | experiment_observations | experiment_id、sensor_data_id、student_id、content、recorded_at | 学生观察记录 |
| `Notification` | notifications | user_id、type、title、content、link、is_read | 站内通知（v4.1） |
| `DeviceToken` | device_tokens | token(唯一索引)、group_id(FK)、device_type、device_name、node_id(FK)、is_active、last_used_at | 设备鉴权令牌（v4.1） |
| `PestDiagnosis` | pest_diagnoses | group_id、node_id、device_token_id、image_url、diagnosis_result、confidence、suggestion | 病虫害诊断（v4.1） |
| `McpCallLog` | mcp_call_logs | group_id、device_token_id、tool_name、arguments(JSON)、result(JSON)、duration_ms、success、error_message、expires_at | MCP 调用日志（v4.1，30 天过期） |
| `ChatSession` | chat_sessions | user_id、title、created_at、updated_at | AI 对话会话（v4.2，用户隔离，级联删除消息） |
| `ChatMessage` | chat_messages | session_id(FK)、role、content、model_used、created_at | AI 对话消息（v4.2） |
| `AiQuotaUsage` | ai_quota_usage | user_id、date(UNIQUE)、count | AI 每日配额计数（v4.2，删除会话不重置） |

#### 核心关系

- `DeviceNode 1—N Component`（级联删除）
- `Classroom 1—N Group —1 DeviceNode`（小组绑定一个节点）
- `Group 1—N User(student)`（group_id 外键）
- `ClassTask 1—N TaskSubmission 1—N SubmissionFile`（级联删除）
- `Experiment 1—N ExperimentGroup`、`Experiment 1—N ExperimentObservation`
- `DeviceToken N—1 Group`、`DeviceToken N—1 DeviceNode`

### 4.5 Schema 层 (`app/schemas/`)

Pydantic v2 模型，与 ORM 实体一一对应，承担请求体校验与响应序列化。命名约定：

- `XxxCreate` — POST 请求体（含必填字段 + 校验规则）
- `XxxUpdate` — PATCH 请求体（所有字段可选）
- `XxxResponse` / `XxxOut` — 响应模型（`from_attributes=True` 从 ORM 转换）

**特殊 Schema：**
- [user.py](file:///d:/IoT/app/schemas/user.py) — `_validate_password_complexity` 校验器：至少 8 位且含字母+数字。
- [token.py](file:///d:/IoT/app/schemas/token.py) — OAuth2 登录响应 `{access_token, token_type, role, user_id}`。
- [mcp.py](file:///d:/IoT/app/schemas/mcp.py) — MCP 工具调用请求/响应 + 日志模型。
- [ai.py](file:///d:/IoT/app/schemas/ai.py) — AI 对话请求/响应 Schema（v4.2，ChatRequest / ChatSessionOut / ChatMessageOut / AiQuotaOut）。

### 4.6 业务逻辑层 (`app/services/`)

22 个 service 封装所有业务规则，路由层只做编排。所有 service 在 [`__init__.py`](file:///d:/IoT/app/services/__init__.py) 导出。下表列出关键 service 及其核心函数。

#### 用户与认证

**user_service.py** — 用户 CRUD + 密码认证
- `authenticate(db, username, password)` — 校验用户名/密码/`is_active`，返回 User 或 None
- `create_user(db, user_in)` — 创建用户，密码哈希存储，用户名重复抛 `ValueError`
- `update_user(db, user, user_in)` — 更新（用户名查重、密码重哈希、角色、激活等）

#### 设备与传感器

**device_node_service.py** — 节点与组件管理 + 控制下发
- `control_component(db, component, action, operator_id, message=None)` — **核心控制方法**：更新组件状态 → 写 DeviceOperationLog + OperationLog → 调 `mqtt.publish_component_control` 下发；MQTT 未送达记 warning 但不阻断 DB 提交
- `list_nodes(db, online=None)` / `create_node` / `update_node` / `delete_node`
- `list_components` / `create_component` / `update_component`

**sensor_service.py** — 传感器数据入库 + 规则联动 + 实时广播
- `create_sensor_data(db, data_in)` — **入库主流程**：写 SensorData → 更新节点在线状态 → 调 `rule_service.evaluate_rules` → `ws_manager.broadcast_sync("sensor_data", ...)` 按 node_id 广播
- `build_echarts_data(rows, metrics=None)` — 转 ECharts x/series 结构

**rule_service.py** — 规则 CRUD + 规则引擎
- `evaluate_rules(db, sensor_data)` — **规则引擎核心**：遍历启用规则 → `_compare` 比对阈值 → 命中则查本节点同类型组件 → 控制组件 + 写日志 + MQTT 下发 + WebSocket 广播 `component_status`；返回触发次数
- `create_rule` / `update_rule` / `toggle_rule`

#### 教学管理

**classroom_service.py** — 班级 CRUD（按 teacher_id / subject 过滤）

**group_service.py** — 小组管理 + 批量建学生
- `batch_create_students(db, payload)` — 按 `g{group_id}s{seq}` 生成用户名，统一密码哈希；IntegrityError 回滚提示重试
- `bind_node` / `unbind_node` — 小组绑定/解绑设备节点

**task_service.py** — 任务 CRUD + 发布通知
- `create_task(db, task_in, created_by)` — 建任务后调 `_notify_students_new_task` 给组内学生推送通知
- `_notify_students_new_task` — 经 `notification_service` 建通知 + `ws_manager.send_to_user_sync` 推送；异常不阻断主流程

**submission_service.py** — 作业提交 + 文件上传 + 批阅
- `create_submission(db, task_id, student_id, content, files)` — 提交或覆盖重交（**重交清空 score/feedback/reviewed_at/reviewed_by**）；最多 10 个文件，需 content 或 files 之一
- `_save_upload_files` — 校验类型白名单 + 20MB 限制，存到 `data/submissions`
- `review_submission(db, submission, payload, reviewer_id)` — 写分数（0-100）+ 评语 + 批阅时间 → 推送"已批阅"通知

**student_service.py** — 学生视角数据聚合
- `list_tasks_for_student(db, student)` — 返回本组 + 全组（group_id=None）任务
- `echarts_data_for_student` / `change_student_password`（校验旧密码）

#### 学情分析

**dashboard_service.py** — 总览统计
- `overview(db)` — 节点数/在线数/规则数/任务数/最新传感器
- `component_summary(db)` — 按组件类型聚合 total/on/off/auto

**student_analytics_service.py** — 学情 + 班级驾驶舱
- `get_analytics_for_student(db, student_id)` — 完整学情（summary + 提交频率 + 得分趋势 + 近 10 条活动）
- `build_analytics_echarts(db, student_id)` — ECharts 图表数据
- `get_classroom_overview(db, classroom_id)` — **班级驾驶舱**：小组排行 + 任务统计 + 评分分布 + 按时率 + ECharts（v4.1）

#### 资源管理

**courseware_service.py** — 课件管理（个人库 + 公共检索）；删除时清理物理文件
**teaching_resource_service.py** — 教学资源分发；`list_resources_for_student` 按本组/本班/全公开过滤
**experiment_service.py** — 实验管理（CRUD + 分组 + 观察记录）
**crop_service.py** — 作物 CRUD（name 唯一）

#### 实时与日志

**notification_service.py** — 站内通知
- `create_notification_for_users(db, user_ids, ...)` — 批量建通知（flush 不 commit）
- `mark_all_as_read(db, user_id)` — 全部已读
- `get_admin_and_teacher_ids(db)` — 取所有激活 admin+teacher（设备告警用）

**log_service.py** — 三类日志写入/查询
- `create_operation_log` — 写用户操作日志
- `list_device_logs` / `list_rule_logs`

#### v4.1 新增服务

**device_token_service.py** — 设备令牌签发/校验
- `create_token(db, payload)` — `secrets.token_urlsafe(32)` 生成；同组同类唯一；明文仅创建/重置时返回一次
- `verify_token(db, token_str)` — 校验有效性并更新 `last_used_at`；无效/吊销返回 None
- `reset_token` / `revoke_token` / `delete_token`

**pest_diagnosis_service.py** — 病虫害诊断（ResNet50 真实推理）
- `_load_model()` — PyTorch 模型懒加载单例（首次推理时加载，之后复用；自动检测 CUDA）
- `ai_classify(image_data)` — bytes → PIL Image → tensor → ResNet50 推理 → (DiagnosisResult, softmax 置信度)
- `create_diagnosis(db, group_id, node_id, ...)` — 推理 + 保存 + WebSocket 广播 `pest_diagnosis` + 通知 admin/teacher
- `cleanup_old_diagnoses(db)` — 清理 30 天以上记录与图片
- 模型文件：`models/pest_model.pth`（可通过 `PEST_MODEL_PATH` 环境变量覆盖）
- 测试环境：`tests/conftest.py` 的 `_mock_ai_classify` autouse fixture 用 monkeypatch 替换 `ai_classify`

**export_service.py** — 学生成长档案 PDF（reportlab + STSong-Light 中文字体）
- `export_student_growth_pdf(db, student_id) -> bytes` — 6 段：封面 / 学习概览 / 得分趋势折线图 / 提交频率条形图 / 近期活动 / 教师评语

**mcp_service.py** — 小智 AI MCP 工具分发（**安全 scope 到 device.group_id**）
- `list_tools()` — 返回 6 个工具的 JSON Schema
- `call_tool(db, device, tool_name, arguments)` — **核心分发器**：校验工具名 → 计时执行 → 写 McpCallLog → 返回 `{success, result, error, duration_ms}`
- 6 个工具：
  - `_tool_get_latest_sensor_data` — 本组最新传感器
  - `_tool_control_components_by_type` — 按类型批量控制本组执行器
  - `_tool_get_group_components` — 本组执行器状态
  - `_tool_get_crop_status` — 本组作物信息
  - `_tool_list_pending_tasks` — 本组未完成任务
  - `_tool_list_group_rules` — 本组适用规则

**ai_service.py** — AI 教学助手（v4.2，DeepSeek API）
- `stream_chat(db, user, session, message, context, is_new_session)` — **核心流式对话**：校验 API Key 和配额 → 构建系统提示词 →
  SSE 逐 token 流式生成 → 完成时保存消息 + 更新会话标题 → 失败时装饰性配额回退 + 清理空会话
- `select_model(message)` — 关键词规则匹配双模型切换（chat / reasoner）
- `get_or_create_session(db, user, session_id)` — 恢复或创建会话
- `get_sessions(db, user, skip, limit)` — 用户会话列表（按 updated_at 倒序）
- `get_messages(db, session_id, user)` — 会话消息列表（校验所有权）
- `delete_session(db, session_id, user)` — 删除会话（级联删除消息）
- `get_quota(db, user)` — 获取今日配额使用情况
- `decrement_quota(db, user)` — 回退配额（API 调用失败时）
- `cleanup_old_sessions(days=180)` — 清理过期会话

### 4.7 路由层 (`app/routers/`)

23 个路由文件，122 个端点。统一前缀 `/api/v1`（`ws.py` 除外）。命名约定：每个文件定义 `router = APIRouter(prefix="/xxx", tags=["xxx"])`，通过 `Depends(get_db)` 注入 DB，`Depends(require_roles(...))` 或 `Depends(get_device_context)` 控制权限。

| 路由文件 | 前缀 | 权限 | 核心端点 |
|----------|------|------|----------|
| [auth.py](file:///d:/IoT/app/routers/auth.py) | /auth | 公开/已登录 | `POST /login`（OAuth2 表单）、`GET /me` |
| [users.py](file:///d:/IoT/app/routers/users.py) | /users | admin | 用户 CRUD |
| [device_nodes.py](file:///d:/IoT/app/routers/device_nodes.py) | /device-nodes | 已登录/admin+teacher | 节点 CRUD + 组件 CRUD + `/control` |
| [device_tokens.py](file:///d:/IoT/app/routers/device_tokens.py) | /device-tokens | admin+teacher | 设备令牌签发/重置/吊销/删除 |
| [sensors.py](file:///d:/IoT/app/routers/sensors.py) | /sensors | admin+teacher | 数据上报（触发规则引擎）/查询/echarts |
| [rules.py](file:///d:/IoT/app/routers/rules.py) | /rules | admin+teacher | 规则 CRUD + toggle + logs |
| [classrooms.py](file:///d:/IoT/app/routers/classrooms.py) | /classrooms | admin+teacher | 班级 CRUD |
| [groups.py](file:///d:/IoT/app/routers/groups.py) | /groups | admin+teacher | 小组 CRUD + bind/unbind + 批量建学生 |
| [tasks.py](file:///d:/IoT/app/routers/tasks.py) | /tasks | admin+teacher | 任务 CRUD |
| [submissions.py](file:///d:/IoT/app/routers/submissions.py) | /submissions | student/admin+teacher | 提交（multipart）/批阅 |
| [student.py](file:///d:/IoT/app/routers/student.py) | /student/me | student | 学生专属接口（小组/任务/传感器/实验/头像/密码） |
| [crops.py](file:///d:/IoT/app/routers/crops.py) | /crops | admin+teacher | 作物 CRUD |
| [logs.py](file:///d:/IoT/app/routers/logs.py) | /logs | admin/admin+teacher | 操作/设备/规则日志 |
| [dashboard.py](file:///d:/IoT/app/routers/dashboard.py) | /dashboard | admin+teacher | overview + component-summary |
| [analytics.py](file:///d:/IoT/app/routers/analytics.py) | /analytics | admin+teacher/student | 学生画像 + 班级驾驶舱 |
| [courseware.py](file:///d:/IoT/app/routers/courseware.py) | /courseware | admin+teacher | 课件库（含所有权校验） |
| [teaching_resources.py](file:///d:/IoT/app/routers/teaching_resources.py) | /resources | admin+teacher | 教学资源（含所有权校验） |
| [experiments.py](file:///d:/IoT/app/routers/experiments.py) | /experiments | 已登录/admin+teacher | 实验 + 分组 + 观察 |
| [notifications.py](file:///d:/IoT/app/routers/notifications.py) | /notifications | 已登录 | 通知列表/未读数/已读 |
| [exports.py](file:///d:/IoT/app/routers/exports.py) | /exports | admin+teacher | `GET /students/{id}/growth-pdf`（RFC 5987 中文文件名） |
| [pest_diagnoses.py](file:///d:/IoT/app/routers/pest_diagnoses.py) | /pest-diagnoses | 设备 token/admin+teacher | 设备上传诊断 + 管理端查询 |
| [mcp.py](file:///d:/IoT/app/routers/mcp.py) | /mcp | 设备 token/admin+teacher | `GET /tools` + `POST /tools/call` + `GET /logs` |
| [ai.py](file:///d:/IoT/app/routers/ai.py) | /ai | admin+teacher+student | `POST /sessions`、`GET /sessions`、`DELETE /sessions/{id}`、`GET /messages/{session_id}`、`POST /chat`（SSE 流式）、`GET /quota` |
| [ws.py](file:///d:/IoT/app/routers/ws.py) | /ws | JWT（URL query） | WebSocket 实时推送 |

**约定：** 创建类返回 201，删除类返回 204。

### 4.8 脚本 ([`app/scripts/init_db.py`](file:///d:/IoT/app/scripts/init_db.py))

`init_db()` 在 `main.py` 启动时按 `AUTO_CREATE_DB` 调用：

- `Base.metadata.create_all(engine)` 建表
- 幂等创建初始 admin（按 `INIT_ADMIN_USERNAME` / `INIT_ADMIN_PASSWORD`）
- 按 `INIT_SAMPLE_DATA` 填充示例数据（teacher / operator / 班级 / 小组 / 节点 / 组件 / 规则 / 学生 / 设备 token 等）
- 启动时调用 `cleanup_expired_mcp_logs` + `cleanup_old_diagnoses` 清理过期数据

---

## 5. 前端模块详解

### 5.1 入口与构建

- [main.ts](file:///d:/IoT/frontend/src/main.ts) — 创建 Vue 应用，挂载 Pinia + Router，应用全局样式
- [App.vue](file:///d:/IoT/frontend/src/App.vue) — 根组件，仅 `<router-view/>`
- [vite.config.ts](file:///d:/IoT/frontend/vite.config.ts) — `@` 别名指向 `src`；dev server `0.0.0.0:5173`；代理 `/api`、`/avatars`、`/courseware-files`、`/resource-files`、`/submission-files`、`/pest-images` 到后端 8001；`manualChunks` 拆分 echarts-vendor / vue-vendor
- [styles.css](file:///d:/IoT/frontend/src/styles.css) — 全局样式 + CSS 变量主题（烛光手记深色 / 羊皮纸浅色）

### 5.2 API 层 (`src/api/`)

[http.ts](file:///d:/IoT/frontend/src/api/http.ts) — Axios 实例：

```typescript
export const http = axios.create({ baseURL: '/api/v1', timeout: 15000 })
// 请求拦截：自动注入 Authorization: Bearer <token>
// 响应拦截：401 → auth.logout() + window.location.href 跳 /login?redirect=...
```

其余 23 个模块（auth/users/device_nodes/sensors/rules/classrooms/groups/tasks/submissions/student/crops/logs/dashboard/analytics/courseware/resources/experiments/notifications/device_tokens/pest_diagnosis/mcp/ai）均基于 `http` 封装对应资源的 CRUD 请求，自动携带 JWT。

### 5.3 状态管理 ([`src/stores/auth.ts`](file:///d:/IoT/frontend/src/stores/auth.ts))

Pinia `useAuthStore`（组合式风格）：

| 状态 | 说明 |
|------|------|
| `token` / `user` | 从 localStorage 恢复（`TOKEN_KEY` / `USER_KEY`） |
| `isAuthenticated` | computed，token + user 均存在 |
| `isReady` | 首次 `syncMe` 完成标记（路由守卫等待） |

| 方法 | 说明 |
|------|------|
| `login(username, password)` | 调登录 API → 存 token → `fetchMe` → 持久化 |
| `syncMe()` | 用 token 拉 `/auth/me` 校验，失败清空 |
| `logout()` | 清空 token/user + localStorage |
| `updateProfile(patch)` | 局部更新 user 并持久化 |

### 5.4 路由与守卫 ([`src/router/index.ts`](file:///d:/IoT/frontend/src/router/index.ts))

**路由分组：**
- `/login` — 公开
- `/student/*` — `StudentLayout` 子路由（8 个学生页面）
- `/*` — `AdminLayout` 子路由（18 个管理页面）

**`roleAccess` 表** — 路由名 → 允许角色数组（如 `devices: ['admin','teacher']`）。

**`beforeEach` 守卫逻辑：**
1. 未 ready 则 `await auth.syncMe()`
2. `requiresAuth` 但未登录 → 跳 `/login?redirect=`
3. 已登录访问 `/login` → 按角色跳默认页（student→student-dashboard，其余→dashboard）
4. 学生只能访问 `/student/*`；非学生不能访问 `/student`
5. 管理端路由按 `roleAccess` 拦截，越权跳默认页

### 5.5 布局与视图

**布局：**
- [AdminLayout.vue](file:///d:/IoT/frontend/src/layouts/AdminLayout.vue) — 管理端：顶栏（标题 + NotificationBell + 主题切换）+ 三组侧边导航（主菜单 / 教学管理 / 系统管理）+ `<router-view/>`
- [StudentLayout.vue](file:///d:/IoT/frontend/src/layouts/StudentLayout.vue) — 学生端：顶栏 + 学生导航 + `<router-view/>`
- 两个布局均 `watch(latestNotification)` 调用 `bellRef.refresh()` 实时刷新未读数

**管理端视图（19 个）：** Dashboard / Devices / Sensors / Rules / Classrooms / Groups / Tasks / Grading / Crops / Logs / Users / StudentAnalytics / ClassroomDashboard / Courseware / Resources / Experiments / PestDiagnosis / McpTools / Login

**学生端视图（8 个，位于 `views/student/`）：** StudentDashboard / StudentTasks / StudentSensor / StudentSubmissions / StudentProfile / StudentResources / StudentExperiments / StudentPestDiagnosis

### 5.6 通用组件与组合式函数

**组件：**
- `StatCard.vue` — 统计数值卡片
- `SectionCard.vue` — 内容区块卡片
- `LineChart.vue` — ECharts 折线图（主题适配）
- `NotificationBell.vue` — 通知铃铛（未读数 + 下拉列表，WebSocket 实时刷新）
- `AiAssistant.vue` — AI 助手悬浮按钮 + 右侧抽屉式聊天界面（v4.2，DeepSeek）
- `AiMessage.vue` — AI 消息气泡（marked + DOMPurify 渲染 Markdown，显示模型标签 chat/深度思考）

**组合式函数：**
- [useTheme.ts](file:///d:/IoT/frontend/src/composables/useTheme.ts) — 主题切换（localStorage 持久化 + 0.35s 过渡）
- [useWebSocket.ts](file:///d:/IoT/frontend/src/composables/useWebSocket.ts) — WebSocket 连接管理：
  - 自动连接 `ws://host/ws?token=jwt`
  - **5 类事件**：`sensor_data` / `component_status` / `device_status` / `pest_diagnosis` / `notification`
  - 30s 心跳（发送 `"ping"`）
  - 指数退避重连（1s→2s→4s→…→30s 上限）
  - 认证失败（4001/4003/1000）不重连
  - 模块级单例，所有组件共享同一连接
  - 数据上限（component_status/device_status 各 50 条，pest_diagnosis 20 条）
  - 登出时 `auth.logout()` 调用 `reset()` 断开并清理
  - `onUnmounted` 自动断开
- [useAI.ts](file:///d:/IoT/frontend/src/composables/useAI.ts) — AI 助手状态管理（v4.2）：会话 CRUD、消息流式接收、配额查询、模型标签标记

---

## 6. 关键类与函数索引

### 后端核心类

| 类 | 位置 | 职责 |
|----|------|------|
| `Settings` | core/config.py | pydantic-settings 配置，`settings` 单例 |
| `Base` | db/base.py | SQLAlchemy declarative_base，所有模型基类 |
| `User` | models/user.py | 用户实体（4 角色） |
| `DeviceNode` / `Component` | models/ | 设备节点 + 组件 |
| `DeviceToken` | models/device_token.py | 设备鉴权令牌（数据隔离核心） |
| `DeviceContext` | core/device_auth.py | 设备身份上下文（token/group_id/node_id/device_type） |
| `WSConnection` | core/websocket_manager.py | WebSocket 连接（user_id/role/node_id） |
| `ConnectionManager` | core/websocket_manager.py | WebSocket 连接池 + 广播（`ws_manager` 单例） |

### 后端核心函数

| 函数 | 位置 | 作用 |
|------|------|------|
| `create_access_token` / `decode_access_token` | core/security.py | JWT 签发/校验 |
| `get_password_hash` / `verify_password` | core/security.py | bcrypt 哈希/校验（72 字节截断） |
| `get_db` | core/dependencies.py | DB Session 依赖 |
| `get_current_user` | core/dependencies.py | JWT → 用户依赖 |
| `require_roles(*roles)` | core/dependencies.py | 角色权限依赖工厂 |
| `get_device_context` | core/device_auth.py | 设备 token 鉴权依赖 |
| `start_mqtt` / `stop_mqtt` | core/mqtt_client.py | MQTT 生命周期 |
| `publish_component_control` | core/mqtt_client.py | 发布控制指令到 MQTT |
| `sensor_service.create_sensor_data` | services/ | 入库 + 规则评估 + WS 广播 |
| `rule_service.evaluate_rules` | services/ | 规则引擎（比对 + 控制 + 日志 + 广播） |
| `device_node_service.control_component` | services/ | 组件控制 + 日志 + MQTT 下发 |
| `device_token_service.verify_token` | services/ | 设备 token 校验 |
| `mcp_service.call_tool` | services/ | MCP 工具分发 + 日志 |
| `export_service.export_student_growth_pdf` | services/ | PDF 生成 |
| `init_db` | scripts/init_db.py | 建表 + 种子 + 清理 |

### 前端核心

| 导出 | 位置 | 作用 |
|------|------|------|
| `http` | api/http.ts | Axios 实例（自动 JWT + 401 跳转） |
| `useAuthStore` | stores/auth.ts | 认证状态（token/user/login/logout/syncMe） |
| `router` / `roleAccess` | router/index.ts | 路由 + 角色守卫 |
| `useWebSocket()` | composables/useWebSocket.ts | WS 连接 + 5 类事件 + 重连 + 心跳 |
| `useTheme()` | composables/useTheme.ts | 主题切换 |

---

## 7. 依赖关系

### 7.1 后端 Python 依赖（[requirements.txt](file:///d:/IoT/requirements.txt)）

| 包 | 版本 | 用途 |
|----|------|------|
| fastapi | 0.115.0 | Web 框架 |
| uvicorn[standard] | 0.30.6 | ASGI 服务器 |
| SQLAlchemy | 2.0.32 | ORM |
| pydantic | 2.8.2 | 数据校验 |
| pydantic-settings | 2.4.0 | 配置管理 |
| python-jose[cryptography] | 3.3.0 | JWT |
| passlib[bcrypt] | 1.7.4 | 密码哈希 |
| bcrypt | ≥4.0.0,<4.1.0 | bcrypt 后端（与 passlib 兼容性约束） |
| python-multipart | 0.0.9 | 文件上传（multipart） |
| python-dotenv | 1.0.1 | .env 加载 |
| jinja2 | 3.1.4 | 模板 |
| paho-mqtt | 2.1.0 | MQTT 客户端（CallbackAPI v2） |
| reportlab | ≥4.0.0 | PDF 生成 |

### 7.2 前端 npm 依赖（[package.json](file:///d:/IoT/frontend/package.json)）

| 依赖 | 用途 |
|------|------|
| vue ^3.5 | 框架（组合式 API） |
| vue-router ^4.4 | 路由 |
| pinia ^2.2 | 状态管理 |
| axios ^1.7 | HTTP 客户端 |
| echarts ^5.5 | 图表 |
| vite ^5.4 + @vitejs/plugin-vue | 构建 |
| typescript ^5.6 + vue-tsc | 类型检查 |

### 7.3 模块间依赖关系

```
routers ──► dependencies (get_db/require_roles/get_device_context)
   │            │
   │            ▼
   │      services ──► models (ORM)
   │         │  │       ▲
   │         │  └───────┘ (from_attributes)
   │         ├──► mqtt_client (publish_component_control)
   │         ├──► websocket_manager (broadcast_sync / send_to_user_sync)
   │         └──► notification_service (跨 service 通知)
   │
   └──► schemas (请求/响应校验)

mqtt_client ──► sensor_service.create_sensor_data (回调入库)
              └─► ws_manager.broadcast_sync (设备状态广播)

ws.py ──► dependencies.get_current_user (JWT via query)
       └─► ws_manager.connect/disconnect

init_db ──► Base.metadata.create_all
         └─► 各 service (种子数据)
```

**关键耦合点：**
- `sensor_service` ↔ `rule_service`（入库触发规则评估）
- `rule_service` / `device_node_service` → `mqtt_client`（控制下发）
- `mqtt_client` → `sensor_service`（MQTT 回调入库，形成数据闭环）
- service 层 → `ws_manager`（同步桥 `broadcast_sync` 跨线程投递到主事件循环）
- `task_service` / `submission_service` / `pest_diagnosis_service` → `notification_service`（业务事件触发通知）

---

## 8. 认证与权限体系

### 8.1 双轨鉴权

| 鉴权方式 | 适用对象 | 头格式 | 依赖函数 |
|----------|----------|--------|----------|
| 用户 JWT | 浏览器用户（admin/teacher/student） | `Authorization: Bearer <jwt>` | `get_current_user` / `require_roles` |
| 设备 token | ESP32-CAM / ESP32-S3 等硬件 | `Authorization: Bearer <device_token>` | `get_device_context` |

两者共用 Bearer 头但使用不同的 FastAPI security scheme（`OAuth2PasswordBearer` vs `HTTPBearer`），路由二选一。

### 8.2 用户 JWT 流程

1. `POST /api/v1/auth/login`（OAuth2 表单 `application/x-www-form-urlencoded`）→ 返回 `{access_token, token_type, role, user_id}`
2. 前端存 localStorage，Axios 拦截器自动注入 `Authorization`
3. 后端 `get_current_user` 解码 JWT → 查用户 → 校验 `is_active`
4. `require_roles(*roles)` 做角色拦截，不匹配抛 403

**安全约束：**
- 密码复杂度：至少 8 位且含字母 + 数字（`_validate_password_complexity`）
- 登录限流：5 次失败锁定 15 分钟（基于客户端 IP，`rate_limit.py`）
- bcrypt 12 rounds，72 字节截断保护

### 8.3 设备 token 流程

1. admin/teacher 调 `POST /device-tokens` 为某小组签发 token（同组同类唯一）
2. token 明文仅创建/重置时返回一次，DB 存明文（64 字符 `secrets.token_urlsafe(32)`）
3. 设备调用 `/pest-diagnoses` 或 `/mcp/tools/call` 时携带 token
4. `get_device_context` → `device_token_service.verify_token` 校验 + 更新 `last_used_at`
5. `DeviceContext.group_id` 作为业务层数据隔离依据（MCP 工具强制 scope）

### 8.4 角色权限矩阵

| 操作 | admin | teacher | operator | student |
|------|:-----:|:-------:|:--------:|:------:|
| 仪表盘 | ✅ | ✅ | ❌ | ❌ |
| 设备节点查看 | ✅ | ✅ | ✅ | ❌ |
| 设备节点增删改 | ✅ | ✅ | ❌ | ❌ |
| 组件控制 | ✅ | ✅ | ✅ | ❌ |
| 传感器数据 | ✅ | ✅ | ✅ | ❌ |
| 规则管理 | ✅ | ✅ | ❌ | ❌ |
| 班级/小组/任务/批阅 | ✅ | ✅ | ❌ | ❌ |
| 操作日志 | ✅ | ❌ | ❌ | ❌ |
| 用户管理 | ✅ | ❌ | ❌ | ❌ |
| 学生端 `/student/me/*` | — | — | — | ✅ |

---

## 9. 实时通信机制

### 9.1 MQTT（设备 ↔ 后端）

[core/mqtt_client.py](file:///d:/IoT/app/core/mqtt_client.py) 使用 paho-mqtt 2.1.0（CallbackAPI v2）：

| 主题 | 方向 | 用途 |
|------|------|------|
| `greenhouse/sensor/data` | ESP32 → 后端 | 传感器数据上报 |
| `greenhouse/device/status` | ESP32 → 后端 | 设备上下线状态 |
| `greenhouse/device/control` | 后端 → ESP32 | 组件控制指令 |

- **回调**：`_on_connect`（订阅两个主题）/ `_on_disconnect`（记日志，依赖 paho 自动重连）/ `_on_message`（按 topic 分发到 `_handle_sensor_data` / `_handle_device_status`）
- **自动重连**：`reconnect_delay_set(min_delay=1, max_delay=120)` 指数退避
- **容错**：`publish_component_control` 在 broker 断连时返回 False，DB 仍提交，仅记 warning
- **设备离线告警**：`_handle_device_status` 检测在线→离线时通知所有 admin+teacher

### 9.2 WebSocket（后端 → 浏览器）

[core/websocket_manager.py](file:///d:/IoT/app/core/websocket_manager.py) 的 `ConnectionManager`（`ws_manager` 单例）：

- **连接池**：`dict[user_id, list[WSConnection]]`，每个 `WSConnection` 含 `websocket / user_id / role / node_id`
- **数据隔离**：`WSConnection.node_id` 为 None（教师/admin 看全部）或 int（学生只看本组）
- **广播**：`broadcast(event_type, data, node_id=None)` 按 node_id 过滤；`broadcast_sync` 是同步包装器，用 `asyncio.run_coroutine_threadsafe` 跨线程投递（供 paho 回调 / service 同步上下文使用）
- **定向推送**：`send_to_user` / `send_to_user_sync` 按 user_id 精确投递（通知场景）

**5 类推送事件：**

| type | 触发场景 | data |
|------|----------|------|
| `sensor_data` | 传感器入库 | SensorData 行 |
| `component_status` | 规则触发控制 | component_id/node_id/type/status/triggered_by_rule |
| `device_status` | 设备上下线 | node_id/online/last_reported_at |
| `pest_diagnosis` | ESP32-CAM 上传诊断 | id/group_id/node_id/image_url/diagnosis_result/confidence/suggestion |
| `notification` | 任务发布/批阅/设备告警 | id/title/content/link/is_read |

**连接认证**：URL 查询参数 `?token=<jwt>`；心跳 30s `"ping"`→`"pong"`；前端指数退避重连。

---

## 10. 项目运行方式

### 10.1 环境要求

- Python 3.10+
- Node.js 18+ / npm 9+
-（可选）Mosquitto MQTT Broker

### 10.2 后端启动

```bash
# 1. 创建并激活虚拟环境
python -m venv .venv
.\.venv\Scripts\activate         # Windows
# source .venv/bin/activate      # macOS / Linux

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化数据库（建表 + 种子数据）
python -m app.scripts.init_db

# 4. 启动 API（开发模式）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

启动后：
- Swagger UI：http://127.0.0.1:8001/docs
- 健康检查：http://127.0.0.1:8001/health

### 10.3 MQTT Broker（可选，IoT 设备通信）

```bash
# Windows：从 https://mosquitto.org/download/ 安装
mosquitto -v
# Linux
sudo apt install mosquitto && sudo systemctl start mosquitto
```

### 10.4 前端启动

```bash
cd frontend
npm install
npm run dev          # 开发服务器 http://localhost:5173
# 或
npm run build        # 生产构建（vue-tsc 类型检查 + vite 打包）
```

> Vite dev server 自动代理 `/api` 与各静态文件路径到后端 8001，无需额外配置。

### 10.5 默认账号

| 角色 | 用户名 | 密码 | 权限 |
|------|--------|------|------|
| 管理员 | admin | 见 `.env` 中 `INIT_ADMIN_PASSWORD` | 所有权限 |
| 教师 | teacher | Teacher123456 | 教学管理 |
| 学生 | g1s1 | Student123456 | 学生端 |

> 学生账号由教师在"小组概览"批量创建，命名规则 `g{组号}s{序号}`。

### 10.6 关键配置（`.env`）

| 变量 | 默认 | 说明 |
|------|------|------|
| `DATABASE_URL` | mysql+pymysql://root:CHANGE_ME@localhost:3306/greenhouse?charset=utf8mb4 | MySQL 连接（必须通过 .env 配置） |
| `JWT_SECRET_KEY` | — | JWT 密钥（生产必改） |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 1440 | Token 有效期 |
| `CORS_ORIGINS` | * | 跨域来源 |
| `AUTO_CREATE_DB` | true | 启动自动建表 |
| `INIT_SAMPLE_DATA` | true | 填充示例数据 |
| `MQTT_BROKER_HOST` | localhost | MQTT 地址 |
| `MQTT_BROKER_PORT` | 1883 | MQTT 端口 |

### 10.7 MySQL 数据库初始化

项目默认使用 MySQL 8.0。首次使用步骤：

```bash
# 1. 创建数据库（utf8mb4 支持中文和 emoji）
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS greenhouse CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. 在 .env 配置连接串
# DATABASE_URL=mysql+pymysql://root:密码@localhost:3306/greenhouse?charset=utf8mb4

# 3. 安装驱动（已在 requirements.txt）
pip install pymysql

# 4. 初始化表 + 种子数据
python -m app.scripts.init_db
```

> 测试环境（pytest）使用 SQLite 内存数据库，无需 MySQL 即可运行测试。

### 10.8 生产部署建议

```bash
# Gunicorn + Uvicorn workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001
```

- 修改 `JWT_SECRET_KEY` 为强随机串
- `CORS_ORIGINS` 设为具体前端域名
- MySQL 连接池配置 `pool_recycle=3600`（避免 8 小时空闲断开）
- Nginx 反向代理，前端静态文件由 Nginx 直接提供

---

## 11. 测试体系

### 11.1 测试结构（[tests/](file:///d:/IoT/tests)）

| 文件 | 类型 | 说明 |
|------|------|------|
| [conftest.py](file:///d:/IoT/tests/conftest.py) | 公共配置 | pytest fixtures（含 `student_token` / 测试 DB） |
| [test_unit.py](file:///d:/IoT/tests/test_unit.py) | 单元测试 | Schema / 枚举校验 |
| [test_api.py](file:///d:/IoT/tests/test_api.py) | API 集成测试 | 全部端点（含设备鉴权 / 病虫害诊断 / MCP） |
| [test_e2e.py](file:///d:/IoT/tests/test_e2e.py) | 端到端测试 | 完整教学流程 |

**共计 365 项测试全部通过。**

### 11.2 运行测试

```bash
# 全部测试
pytest tests/ -v

# 分类运行
pytest tests/test_unit.py -v
pytest tests/test_api.py -v
pytest tests/test_e2e.py -v

# 覆盖率报告
pytest tests/ --cov=app --cov-report=html
```

### 11.3 教师端 E2E 冒烟测试

```bash
# 启动后端后运行
python scripts/smoke_test_teacher.py
```

覆盖完整教学闭环：管理员登录 → 创建班级 → 创建小组 → 绑定节点 → 批量创建学生 → 学生登录 → 提交作业 → 教师批阅 → 仪表盘统计（19 项）。

---

## 附录：版本演进要点

| 版本 | 关键特性 |
|------|----------|
| v3.2 | DeviceNode + Component 模型重构（替代旧 Device 模型） |
| v3.4 | 课件库 + 教学资源 + 学生画像 |
| v4.0 | WebSocket 实时推送 + 科学实验管理 |
| v4.1 | 通知系统（P0-1）、班级驾驶舱（P0-2）、学生成长档案 PDF（P0-3）、设备鉴权令牌（P0-NEW-0）、ESP32-CAM 病虫害诊断（P0-NEW-1）、ESP32-S3 小智 AI MCP（P0-NEW-2） |

> 更多产品级说明见 [README.md](file:///d:/IoT/README.md) 与 [CONTEXT.md](file:///d:/IoT/CONTEXT.md)。
