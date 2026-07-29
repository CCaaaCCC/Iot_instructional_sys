# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Smart greenhouse teaching management platform for primary school science/labor classes. FastAPI backend + Vue 3 frontend + MQTT for IoT device communication. Three user roles: admin, teacher, student.

## Commands

```bash
# Backend
pip install -r requirements.txt                          # Install dependencies
python -m app.scripts.init_db                            # Initialize DB + seed data + migrations
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 # Start dev server

# Frontend
cd frontend && npm install && npm run dev                # Start Vite dev server (:5173)
cd frontend && npm run build                             # Production build (vue-tsc + vite)

# Testing
pytest tests/ -v                                         # All tests (365 items)
pytest tests/test_unit.py -v                             # Schema/enum unit tests
pytest tests/test_api.py -v                              # API integration tests
pytest tests/test_e2e.py -v                              # E2E flow tests
pytest tests/ --cov=app --cov-report=html                # Coverage report
python scripts/smoke_test_teacher.py                     # Teacher E2E smoke test (needs backend running)

# MQTT Broker (optional, for IoT communication)
mosquitto -v                                             # Start Mosquitto locally

# Hardware Simulation (for testing without physical devices)
python simulate_hardware.py --node-id 1 [--interval 5] [--duration 0]  # 0 = infinite
python mcp_bridge.py                                         # MCP bridge to xiaozhi.me
```

## Architecture

### IoT Hardware — Four Device Types

| Device | Role | Communication | Auth |
|--------|------|--------------|------|
| **ESP32** | Main node: sensors + actuators (fan/pump/light) | MQTT (`greenhouse/sensor/data`, `greenhouse/device/control`) | Device token via `get_device_context` for HTTP, MQTT publishes as device |
| **ESP32-CAM** | Camera: plant pest diagnosis image upload | HTTP POST `/api/v1/pest-diagnoses/upload` | Device token (only `esp32cam` type allowed) |
| **ESP32-S3 (小智 AI)** | Voice AI assistant: queries sensor data, controls actuators, checks tasks/crops | HTTP via MCP protocol: `GET /mcp/tools`, `POST /mcp/tools/call` | Device token (6 read+control tools, all auto-scoped to `group_id`) |
| **ESP32-S3 Monitor** | TFT dashboard upper computer: reports sensor data + receives actuator control commands via UART to lower computer | MQTT (`greenhouse/sensor/data`, `greenhouse/device/control`, `greenhouse/device/status`) | MQTT publishes as device (no token auth on broker); device token for HTTP if needed |

Each group has device tokens (one per device type), all bound to the same `group_id`. Tokens are created/reset/revoked via `/device-tokens` endpoints.

> **Note on `esp32s3` vs `esp32s3_monitor`**: These are two physically distinct ESP32-S3 boards. `esp32s3` is the 小智 AI voice assistant (MCP protocol); `esp32s3_monitor` is the TFT dashboard upper computer (MQTT protocol, reports sensor data + receives control commands). Do not confuse them.

### Layered Backend (3-tier)

```
routers/  →  services/  →  models/ (SQLAlchemy ORM, no repository layer)
    ↓
schemas/ (Pydantic v2 — request/response validation)
```

- **Routers** are thin: parse input → call service → return result. Catch `ValueError` → HTTP 400. After mutating operations, call `log_service.create_operation_log(db, ...)` for audit trail.
- **Services** contain all business logic. They receive `db: Session` as first param and use SQLAlchemy 2.0-style `select()` / `db.get()` / `db.execute()`. Services call other services directly (e.g., `sensor_service.create_sensor_data` calls `rule_service.evaluate_rules`).
- **Models** define `id` as auto-increment PK. Use `from app.models.enums import *` for enum types. `UserRole`, `ComponentType`, `ComponentStatus`, `SensorMetric`, `RuleOperator`, `TaskStatus`, `CourseSubject`, `TaskType`, `ExperimentStatus`, `ExperimentRole`, `DeviceType` (esp32/esp32cam/esp32s3/esp32s3_monitor), `DiagnosisResult` (5 plant disease categories: tomato/strawberry × healthy/disease).
- **Schemas** mirror models with `*Create` (input), `*Out` (response with `model_config = ConfigDict(from_attributes=True)`), `*Update` (optional fields).

### Operation Logging Pattern

All mutating router endpoints call `log_service.create_operation_log()` to record an audit trail:

```python
log_service.create_operation_log(
    db, user_id=current_user.id, action="create_device_token",
    entity_type="device_token", entity_id=str(token.id),
    detail=f"Issued {token.device_type.value} token for group {token.group_id}",
)
```

The `operation_logs` table stores user_id, action, entity_type, entity_id, and detail. This pattern is used across _all_ routers (devices, tokens, users, crops, experiments, pest diagnoses, etc.).

### File Upload Pattern — Two Variants

**Single-file entity** (courseware, teaching resources, avatars):
Router uses `Form()` for metadata fields + `file: UploadFile = File(...)` → saves to `data/<entity>/` → stores `file_url` in one DB column. Deletes disk file on record delete. Filename format: `{timestamp}_{random_hex}.{ext}`.

**Multi-file per record** (task submissions):
Uses a separate `submission_files` table (one-to-many). Router accepts `files: list[UploadFile] = File(default=[])`. Service handles file validation, disk save, DB row creation, and cleanup. On re-submission without new files, existing files are preserved (`files=None` = keep, `files=[]` = not sent). Service layer validates MIME type + size. Disk cleanup on both submission replacement and task deletion (`task_service.delete_task` iterates submissions). Filename format: `{submission_id}_{ts}_{idx}_{original_name}`.

### Data Directory Structure

```
data/                         # File upload storage (database managed by MySQL)
  avatars/                   # User profile photos (mounted at /avatars)
  courseware/                # Teacher courseware files (mounted at /courseware-files)
  resources/                 # Teaching resource files (mounted at /resource-files)
  submissions/               # Student task submissions (mounted at /submission-files)
  pest-images/               # ESP32-CAM uploads (mounted at /pest-images)
```

Each directory is created at startup in `app/main.py` via `StaticFiles` mount with `mkdir(parents=True, exist_ok=True)`.

### Dependency Injection Chain

```
get_db() → SessionLocal (yield, finally close)
get_current_user(db, token) → decode JWT → get_user_by_id → check is_active
require_roles(*roles) → wraps get_current_user → checks role in roles
get_device_context(db, credentials) → verify device token → DeviceContext(token, group_id, node_id, device_type)
```

Two independent auth tracks coexist:
- **User JWT** (`oauth2_scheme`): for admin/teacher/operator/student endpoints via `require_roles`
- **Device token** (`get_device_context` in `app/core/device_auth.py`): for ESP32/ESP32-CAM/ESP32-S3 hardware endpoints. Uses a separate `HTTPBearer` instance with `auto_error=False`. Returns `DeviceContext` dataclass with `token`, `group_id`, `node_id`, `device_type`. All device-scoped tools automatically use `group_id` for data isolation — never accept external `group_id` from request body.

Login uses OAuth2 form format (`application/x-www-form-urlencoded`), NOT JSON. Token URL: `{API_V1_STR}/auth/login`.

### Config: `app/core/config.py`

Uses `pydantic-settings` with `.env` file auto-load. All settings accessed via `from app.core.config import settings` singleton. Key env vars:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `mysql+pymysql://root:CHANGE_ME@localhost:3306/greenhouse?charset=utf8mb4` | MySQL connection (must override via .env) |
| `JWT_SECRET_KEY` | (required) | HMAC signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 1440 (24h) | JWT lifetime |
| `CORS_ORIGINS` | `*` | CORS allowed origins |
| `MQTT_BROKER_HOST` | `localhost` | Mosquitto address |
| `INIT_ADMIN_USERNAME` | `admin` | Seed admin user |
| `INIT_ADMIN_PASSWORD` | `Admin123456` | Seed admin password |
| `INIT_SAMPLE_DATA` | `true` | Seed classrooms/groups/devices |
| `AUTO_CREATE_DB` | `true` | Auto-init tables at startup |

### Security Notes

- **bcrypt 72-byte limit**: `get_password_hash()` truncates passwords to `password[:72]` before hashing.
- **bcrypt version**: locked to `>=4.0.0,<4.1.0` due to passlib compat issues.
- **JWT sub** is a `user_id` string — converted to `int` in `get_current_user()`.
- **Login rate limit**: in-memory dict, 5 failures → 15-minute lock per IP. Clears on process restart.
- **Password complexity**: minimum 8 chars, must contain both letters and digits.
- **File upload limits**: avatars 2MB (jpg/png/webp), courseware/resources 50MB (ppt/pptx/pdf/mp4/doc/docx/txt), **submissions 20MB** per file, max 10 files (images/pdfs/ppts/docs/txt/mp4), pest images 10MB (jpg/png).
- **File storage mounted paths**: `/avatars`, `/courseware-files`, `/resource-files`, `/submission-files`, `/pest-images`.

### Database: `app/db/session.py`

- Module-level `engine` and `SessionLocal`. **Do not** create additional engines.
- MySQL: `pool_pre_ping=True` (connection liveness check) + `pool_recycle=3600` (hourly recycle to avoid MySQL `wait_timeout` disconnect). InnoDB engine enables foreign keys by default (no PRAGMA needed).
- `AUTO_CREATE_DB=true` triggers `init_db()` at startup (creates tables via `Base.metadata.create_all()`, seeds admin + sample data if not present).
- Test environment (`tests/conftest.py`) still uses SQLite in-memory DB for speed and isolation.

### Schema Migrations

No Alembic. Schema changes are applied by `Base.metadata.create_all()` in `app/scripts/init_db.py` (creates tables that don't exist). For existing tables needing schema changes, delete the MySQL database and re-run `init_db()` (dev data is disposable). Historical SQLite PRAGMA-based migrations have been removed after the MySQL migration.

### MQTT Integration + WebSocket: `app/core/mqtt_client.py` + `app/core/websocket_manager.py`

- **MQTT** managed via FastAPI lifespan: `start_mqtt()` at startup, `stop_mqtt()` at shutdown. Auto-reconnect with exponential backoff (1s→120s).
- Subscribes to `greenhouse/sensor/data` and `greenhouse/device/status`. Publishes control commands to `greenhouse/device/control`.
- **Control payload** (`publish_component_control`) includes `component_type` field (fan/pump/light) so MQTT devices (e.g. `esp32s3_monitor`) can map directly to actuators without reverse-looking-up the DB. The field is backward-compatible (omitted when empty).
- Health check at `GET /health` returns `{"status": "ok", "mqtt": "connected|disconnected"}`.
- **WebSocket** (`/ws?token={jwt}`) pushes real-time events to frontend via `ConnectionManager` singleton.
- Events: `sensor_data`, `component_status`, `device_status`, `pest_diagnosis`, `notification`. Scoped by `node_id` — students only see their group's data.
- MQTT → WebSocket bridge: `sensor_service.create_sensor_data()`, `rule_service.evaluate_rules()`, `mqtt_client._handle_device_status()` each call `ws_manager.broadcast_sync()`.
- Thread safety: `broadcast_sync` uses `asyncio.run_coroutine_threadsafe()` from paho-mqtt callback threads.

### Rule Engine Trigger Chain (with WebSocket broadcast)

`sensor_service.create_sensor_data()` → `db.flush()` → `rule_service.evaluate_rules(db, sensor_data)` → iterates enabled rules → compares metric to threshold → updates matching components → writes `RuleLog`, `DeviceOperationLog`, `OperationLog` → publishes MQTT control commands → `ws_manager.broadcast_sync("component_status", ...)` → `db.commit()` → `ws_manager.broadcast_sync("sensor_data", ...)`.

### Pest Diagnosis (ESP32-CAM) Flow

1. ESP32-CAM uploads image via `POST /pest-diagnoses/upload` (device token auth, only `esp32cam` type allowed)
2. Image saved to `data/pest-images/` as `{device_token_id}_{unix_ts}_{random_hex}.{ext}`
3. `pest_diagnosis_service.create_diagnosis()` runs **ResNet50 真实推理** — PyTorch 模型懒加载（首次推理时加载，之后复用），对图片进行 5 分类（番茄/草莓 × 健康/病害），返回 Top-1 类别 + softmax 置信度。模型文件位于 `models/pest_model.pth`，可通过环境变量 `PEST_MODEL_PATH` 覆盖。自动检测 CUDA（有 GPU 时用 GPU，否则 CPU）。
4. Result pushed via WebSocket (`pest_diagnosis` event, scoped to `node_id`)
5. Notification created for admin + teacher users with link to pest diagnosis page

> **测试环境**：`tests/conftest.py` 的 `_mock_ai_classify` autouse fixture 用 monkeypatch 替换 `ai_classify` 为确定性哈希分类（无需安装 PyTorch/模型文件）。

### MCP Integration (ESP32-S3 / 小智 AI)

The ESP32-S3 "小智 AI" device uses a **Model Context Protocol** interface (6 tools, all auto-scoped to `device.group_id`):

```python
# Tool dispatch table in app/services/mcp_service.py
_TOOL_DISPATCH = {
    "get_latest_sensor_data":  # Returns latest sensor readings for the group
    "control_components_by_type":  # Batch control all fan/pump/light by type (voice-friendly)
    "get_group_components":  # List all actuator states
    "get_crop_status":  # Query crop growth info
    "list_pending_tasks":  # List incomplete class tasks (default limit=5)
    "list_group_rules":  # Return enabled rules scoped to this group's node
}
```

Key design points:
- **Auth**: Device token (`get_device_context`), not user JWT
- **Scoping**: Every tool resolves `group_id` from the device token — never accepts external `group_id`
- **Logging**: Every call writes `McpCallLog` with `duration_ms` + `expires_at=now+30d` (auto-cleanup)
- **Tools available**: GET `/mcp/tools` lists tool definitions, POST `/mcp/tools/call` dispatches
- **Logs viewable**: GET `/mcp/logs` (admin/teacher/operator only) for audit

### API Conventions

- Base prefix: `/api/v1`. Create returns 201. Delete returns 204. Get returns 200. Update returns 200.
- List endpoints support query filters and use `skip`/`limit` (0-based offset).
- ECharts endpoints return `{ x: [...timestamps], series: [{ name, data: [...] }] }`.
- File upload endpoints use `multipart/form-data` (FormData), not JSON body.

### Frontend Architecture

- **Vue 3 Composition API + TypeScript + Vite 5**. Pinia for auth state. Vue Router with role-based guards.
- **Route structure**: `/student/*` (StudentLayout) vs `/*` (AdminLayout). Logged-in students are forced to `/student`, non-students can't access `/student`.
- **Role-based access** (`frontend/src/router/index.ts`): Each admin route has a `roleAccess` map. Students are blocked at guard level before any admin route check. Operator has limited access (devices, logs, pest-diagnoses, mcp-tools).
- **Shared components** (`frontend/src/components/`): `StatCard.vue`, `SectionCard.vue`, `LineChart.vue` (ECharts wrapper, re-renders on theme change), `NotificationBell.vue`.
- **WebSocket composable** (`frontend/src/composables/useWebSocket.ts`): **模块级单例**（所有组件共享同一连接），auto-connects via native WebSocket API, JWT extracted from localStorage. Exponential backoff reconnect (1s→30s max), 30s heartbeat (`ping`/`pong`). Returns `{ connected, latestSensorData, componentUpdates, deviceStatuses, pestDiagnoses, latestNotification, disconnect, reset }`. 数据有上限（component_status/device_status 各保留 50 条，pest_diagnosis 保留 20 条）。认证失败（4001/4003）不重连。登出时 `auth.logout()` 调用 `reset()` 断开并清理。Both layouts `watch(latestNotification)` to refresh `NotificationBell` in real time.
- **Axios interceptor** (`frontend/src/api/http.ts`): auto-attaches Bearer token from localStorage. 401 → clears auth store → redirects to `/login`.
- **Vite proxy**: `/api`, `/avatars`, `/courseware-files`, `/resource-files`, `/submission-files`, `/pest-images` → `http://127.0.0.1:8001` (configure with `VITE_PROXY_TARGET`).
- **Theme**: CSS variables with `data-theme` attribute. `useTheme` composable persists to localStorage.
- **API modules** (`frontend/src/api/*.ts`): one file per resource, imports shared `http` instance.
- **Types** in `frontend/src/types.ts` mirror backend enums and models exactly (keep in sync when adding enums).

### Test Architecture

- `conftest.py` creates a session-scoped `test_engine` (separate `test_greenhouse.db`), drops/recreates all tables per session.
- `sample_data` fixture populates baseline entities. Each test function gets a fresh `db` session that rolls back on teardown.
- `client` fixture overrides `get_db` dependency to use test DB. Pre-built auth header fixtures for each role.
- Tests are split: `test_unit.py` (schema validation, enum values), `test_api.py` (endpoint integration), `test_e2e.py` (multi-step flows).
- HTTP upload endpoints use `data=` (dict, sent as `multipart/form-data`) not `json=` in tests.

### Teaching Platform Features (v4.0)

Four modules built on top of the IoT layer:

| Module | API Prefix | Purpose | Audience |
|--------|-----------|---------|----------|
| **Student Analytics** | `/analytics` | Aggregated learning stats from existing TaskSubmission/ClassTask data (no new table) | Teacher ↔ Student |
| **Courseware Library** | `/courseware` | Teacher lesson-prep resources; personal library + public sharing (is_public toggle) | Teacher ↔ Teacher |
| **Teaching Resources** | `/resources` | Teacher publishes learning materials (PPT/video/doc) to classrooms/groups; students view/download | Teacher → Student |
| **Experiment Management** | `/experiments` | Scientific experiment lifecycle: hypothesis → variable → control/experimental groups → student observations → conclusion | Teacher ↔ Student |
| **Student Growth PDF** | `/exports` | PDF export of student learning archive (reportlab, Chinese font built-in) | Teacher export |

Student endpoints: `GET /student/me/analytics`, `GET /student/me/resources`, `GET /student/me/experiments/*`.

### AI Assistant (DeepSeek)

Built on DeepSeek API (OpenAI-compatible). Conversational assistant for students (learning help) and teachers (teaching prep). Suspended button + right-side drawer UI, persistent chat history, SSE streaming, dual-model switching.

- **API prefix**: `/ai`. Roles: admin / teacher / student.
- **Data models**: `ChatSession` (user-isolated, cascade delete messages), `ChatMessage` (role/content/model_used), `AiQuotaUsage` (independent `(user_id, date)` UNIQUE counter — deleting sessions never resets quota).
- **Config** (`app/core/config.py`): `DEEPSEEK_API_KEY` (empty = unconfigured, endpoints return 503-like error event), `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL_CHAT` / `DEEPSEEK_MODEL_REASONER`, `AI_DAILY_QUOTA=50`, `AI_CONTEXT_WINDOW=10`, `AI_SESSION_TITLE_MAXLEN=30`, `AI_REQUEST_TIMEOUT=60`.
- **Dual-model switch**: keyword rule matching in `ai_service.select_model()` — messages containing `_REASONER_KEYWORDS` (为什么/分析/解释原理/设计/制定/推理/对比/评估/...) use `deepseek-reasoner`, otherwise `deepseek-chat`.
- **Streaming SSE events** (`POST /ai/chat` returns `StreamingResponse(media_type="text/event-stream")`):
  - `data: {"type":"session","session_id":123}\n\n` (first event when session created)
  - `data: {"type":"delta","content":"片段"}\n\n` (token-by-token output)
  - `data: {"type":"done","message_id":456,"model":"..."}\n\n` (complete)
  - `data: {"type":"error","message":"..."}\n\n` (failure)
- **Quota isolation**: `ai_quota_usage` table committed independently of session lifecycle; users cannot bypass limits by deleting sessions.
- **Quota rollback on failure**: When DeepSeek API call fails or returns empty response, `ai_service.decrement_quota()` rolls back the count so users don't lose quota on errors. Only successful responses (with content) consume quota.
- **Empty session cleanup**: When `POST /ai/chat` creates a new session but `stream_chat` fails early (API unconfigured or quota exceeded), the empty session is deleted via `is_new_session` flag passed from router to service — no orphan "新对话" sessions left in DB.
- **Session isolation**: `ChatSession.user_id == current_user.id` enforced in service layer — teachers cannot read students' conversations (privacy-first).
- **System prompt**: role-aware persona (student: 「棚棚小助手」, 通俗语言, ≤300 字; teacher: 教学助手, 专业简洁, ≤500 字) + page context injection (`ChatContext.route_name` + `page_data`).
- **Frontend**: floating button (bottom-right) + right drawer (`AiAssistant.vue`), `useAI` composable per layout (non-singleton), `AiMessage.vue` renders Markdown via `marked` + `DOMPurify`. Streaming via `XMLHttpRequest` + `onprogress` (EventSource cannot set Authorization header, fetch cannot detect `ERR_ABORTED`). Uses `processedLength` variable to track already-parsed response text. Operator role hides the floating button.
- **Cleanup**: `ai_service.cleanup_old_sessions(days=180)` called by `init_db()` at startup.

### Key Relationships

- `User.group_id` → `Group.id` (students belong to one group, NULL for admin/teacher/operator)
- `Group.class_id` → `Classroom.id`, `Group.node_id` → `DeviceNode.id`
- `DeviceNode` has many `Component` (fan/pump/light/sensor). Components are actuators (on/off/auto) except `type=sensor`.
- `SensorData.node_id` → `DeviceNode.id`
- `ClassTask.group_id` → `Group.id`, `ClassTask.created_by` → `User.id`
- `TaskSubmission.task_id` → `ClassTask.id`, `TaskSubmission.student_id` → `User.id`
- `TaskSubmission` has many `SubmissionFile` (cascade delete-orphan — DB rows cascade, disk files cleaned by service)
- `Rule` triggers on `action_component_type` (not specific component) — finds all components of that type on the node
- `Crop.group_id` → `Group.id`
- `Courseware.owner_id` → `User.id` (teacher-owned, is_public toggle for library sharing)
- `TeachingResource.publisher_id` → `User.id`, optional FKs to `Classroom`/`Group`/`ClassTask`
- `Experiment` + `ExperimentGroup` + `ExperimentObservation` models (v4.0, fully implemented with API + UI)
- `Experiment.class_id` → `Classroom.id`, `ExperimentGroup.group_id` → `Group.id`, `ExperimentObservation.student_id` → `User.id`
- `DeviceToken.group_id` → `Group.id`, `DeviceToken.node_id` → `DeviceNode.id` (3 tokens per group: esp32/esp32cam/esp32s3)
- `McpCallLog.group_id` → `Group.id`, `McpCallLog.device_token_id` → `DeviceToken.id` (30-day retention)
- `ChatSession.user_id` → `User.id` (user-isolated, cascade delete-orphan on messages)
- `ChatMessage.session_id` → `ChatSession.id`
- `AiQuotaUsage(user_id, date)` UNIQUE constraint (independent of session deletion)

### Student Username Convention

Students are batch-created per group. Username format: `g{group_id}s{seq}` (e.g., `g1s2` = group 1, student 2). Seq starts from `existing_count + 1`.

### Adding a New Sensor Metric

1. Add enum value in `app/models/enums.py` → `SensorMetric`
2. Add column in `app/models/sensor_data.py`
3. Add field in `app/schemas/sensor_data.py`
4. Update `app/services/sensor_service.py` handling logic
5. Update `frontend/src/types.ts` → `SensorData` interface
6. Update frontend templates (forms, tables, charts)

### Adding a New Resource with File Upload

**Single-file variant** (like courseware/teaching resources):
1. Create model in `app/models/` (include `file_url`, `file_size`, `owner_id`/`publisher_id` columns)
2. Create schemas in `app/schemas/` (`*Create` with `Field()`, `*Out` with `from_attributes=True`)
3. Create service in `app/services/` (CRUD functions, include file deletion on record delete)
4. Create router in `app/routers/` (use `Form()` params for metadata + `UploadFile = File(...)` for the file; validate content_type and size; save to `data/<entity>/`; store URL path in DB; mount `StaticFiles` in `main.py`)
5. Register in `app/models/__init__.py`, `app/services/__init__.py`, `app/routers/__init__.py`, and `app/main.py`
6. Add Vite proxy in `frontend/vite.config.ts` for the static mount path
7. Create frontend API module + view page; add to `types.ts`, layouts, and router

**Multi-file variant** (like task submissions with `submission_files` table):
Follow the `submission_service.py + SubmissionFile` pattern — separate table, service-level file save/delete helpers, `cascade="all, delete-orphan"` on the parent relationship, and explicit disk cleanup in both the service and the parent's delete function.

### Adding a New Experiment Feature

When adding new experiment-related features, follow the established pattern:

**Backend** (model already exists — add to `app/models/experiment.py`):
1. Add schema fields to `app/schemas/experiment.py` → `ExperimentBase`/`ExperimentUpdate`/`ExperimentOut`
2. Add service functions to `app/services/experiment_service.py` (db-first-param, 3-tier CRUD)
3. Add router endpoints to `app/routers/experiments.py` (include operation logging)
4. Add student-facing endpoints to `app/routers/student.py` (scope via `student_service.get_experiment_for_student`)

**Frontend**:
5. Add API functions to `frontend/src/api/experiments.ts` (if student-facing, to `frontend/src/api/student.ts`)
6. Add or update views in `frontend/src/views/ExperimentsView.vue` (admin) or `frontend/src/views/student/StudentExperimentsView.vue` (student)
7. Register routes in `frontend/src/router/index.ts`, add nav items in layouts

### WebSocket Event Pattern

To add a new real-time event type:

**Backend**:
1. In `app/routers/ws.py` — the `/ws` endpoint auto-dispatches all JSON events; no changes needed unless adding new auth logic
2. At the broadcast source, call: `ws_manager.broadcast_sync("event_type", data_dict, node_id=node_id)`
   - `node_id=None` → broadcasts to all connected clients (teachers/admins)
   - `node_id=N` → broadcasts to teachers + students whose group is on node N
3. Thread safety: `broadcast_sync` uses `asyncio.run_coroutine_threadsafe` — safe from paho-mqtt callbacks

**Frontend**:
4. In `frontend/src/composables/useWebSocket.ts` — add a new `case 'event_type':` in the switch statement
5. In the target view, destructure the new ref from `useWebSocket()` and `watch()` it

### Adding a New MCP Tool

1. Add tool function in `app/services/mcp_service.py` (receives `db: Session, device: DeviceContext, ...`)
2. Register in `_TOOL_DISPATCH` dict and add description to `list_tools()`
3. No router changes needed — dispatch is automatic via the `call_tool` dispatcher
4. Always use `device.group_id` for scoping (never accept external `group_id`)
