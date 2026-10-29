# 智慧大棚教学系统

面向小学劳动课与科学课的智能温室教学管理平台，提供设备节点管理、传感器数据采集、自动规则控制、班级/小组/学生管理、课堂任务发布与作业批阅等完整教学闭环，支持 ESP32 等 IoT 硬件通过 MQTT/HTTP 接入。

## 系统架构

```
┌─ 大棚现场 ───────────────────────────────────────────────────┐
│                                                               │
│  ESP32 设备节点 ──MQTT──┐                                      │
│   ├─ 传感器组件          │                                     │
│   └─ 执行器（风扇/水泵/补光灯）                                │
│                                                               │
│  ESP32-CAM 视觉节点 ──HTTP──┐  （设备 token 鉴权）             │
│   └─ 拍照上传 → 病虫害诊断（ResNet50 5 分类）                 │
│                                                               │
│  ESP32-S3 小智 AI ──HTTP──┐  （设备 token 鉴权）               │
│   └─ MCP 工具调用（6 个工具：传感器/控制/作物/任务）          │
│                                                               │
│  ESP32-S3 TFT 上位机 ──MQTT──┐  （MQTT 设备鉴权）             │
│   ├─ UART 接收下位机传感器数据 → TFT 屏显示 + MQTT 上报云端   │
│   └─ MQTT 接收执行器控制 → UART 下行到下位机（风扇/水泵/灯）  │
│                         ▼                                     │
└─────────────────── FastAPI 后端 :8001 ────────────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
               Mosquitto    MySQL     Vue 前端
               MQTT Broker  数据库    教师/学生后台 :5173
```

## 硬件固件代码

四类设备的固件/边缘代码不在本仓库内，分布在独立工程中。完整盘点（接线、协议、烧录方式）见根目录 **[HARDWARE_CODE.md](HARDWARE_CODE.md)**：

| 路径 | 项目 | 设备 |
|------|------|------|
| `C:\Users\xiezh\Documents\Arduino\greenhouse_lower_node\` | ESP32 下位机：传感器采集 + 执行器控制，UART 对接上位机 | ESP32 主节点 |
| `C:\Users\xiezh\Documents\PlatformIO\Projects\tft_screen_1.9\` | ESP32-S3 双屏上位机（TFT 仪表盘 + OLED 天气），UART ↔ 下位机，MQTT ↔ 后端 | ESP32-S3 Monitor |
| `D:\Project\esp32cam-upload\` | ESP32-CAM 固件：复位自动拍照上传病虫害诊断 | ESP32-CAM |
| `D:\Project\my_model\` | 病虫害分类模型训练/推理（PyTorch），产物拷贝为本仓库 `models/pest_model.pth` | 后端 AI 模型 |

小智 AI（ESP32-S3）固件为小智官方第三方固件，本仓库仅包含其后端 MCP 接口。

## 云端部署实例

当前生产实例已部署到阿里云：

| 项 | 值 |
|----|----|
| 访问地址 | **http://xxxxxxxxxx** |
| 服务器 | 阿里云 ECS，Ubuntu 24.04，2 核 / 2G |
| MQTT | `47.80.57.231:1883`，用户名/密码认证 |
| 部署指南 | [deploy/README.md](deploy/README.md) |
| 部署记录 | [deploy/DEPLOYMENT_RECORD.md](deploy/DEPLOYMENT_RECORD.md) |

> 同机 80 端口由 `gravity_tunnel` 项目占用，本平台使用 8080，未改动现有服务。
> MQTT 密码不写入文档，存放于服务器 `/opt/greenhouse/.env` 与 `/etc/mosquitto/passwd`；烧录固件时请从服务器获取。

## 技术栈

| 层级 | 技术 | 说明 |
|:--|:--|:--|
| 后端框架 | FastAPI 0.115 | 异步 Python Web 框架 |
| ORM | SQLAlchemy 2.0 | 数据库 ORM |
| 数据校验 | Pydantic v2 | 请求/响应校验 |
| 认证 | JWT (python-jose) | OAuth2 Bearer Token |
| 密码加密 | bcrypt (passlib) | 单向哈希 |
| MQTT | paho-mqtt + Mosquitto | IoT 设备通信 |
| 数据库 | MySQL 8.0 | 生产级关系数据库（utf8mb4 字符集） |
| 前端 | Vue 3 + TypeScript | 组合式 API |
| 构建 | Vite 5 | 前端开发与打包 |
| 图表 | ECharts 5 | 传感器曲线 |
| AI 推理 | PyTorch + torchvision | 病虫害诊断 ResNet50 模型（5 分类，CUDA/CPU 自动切换） |

## 功能模块

### 教学管理端（教师/管理员）

| 模块 | 功能描述 |
|------|----------|
| **仪表盘** | 班级概览、待批阅提交、最近任务、组件状态汇总、环境趋势曲线 |
| **设备节点管理** | 创建 ESP32 设备节点，为节点添加组件（风扇/水泵/补光灯/传感器），控制执行器状态 |
| **传感器数据** | 上报环境数据、历史曲线、最新数据、历史列表（WebSocket 实时推送） |
| **规则控制** | 创建自动控制规则（如温度>30℃自动开风扇），支持启用/停用，触发规则引擎 |
| **班级管理** | 创建班级、选择科目（劳动课/科学课）、展开查看小组 |
| **小组概览** | 创建小组、绑定设备节点、批量创建学生账号、查看学生名单 |
| **课堂任务** | 创建任务并指定小组、支持科目（劳动/科学）、任务类型（观察/实验/维护） |
| **批阅中心** | 查看学生提交、打分（0-100）、填写评语、支持重新批阅 |
| **实验管理** | 创建科学实验、设定变量指标/假设、分配对照/实验组、学生记录观察数据 |
| **作物管理** | 维护作物档案、生长阶段、关联小组 |
| **日志中心** | 三类日志：操作审计、设备操作（节点+组件）、规则触发 |
| **用户权限** | 管理员维护管理员/教师账号 |
| **学生画像** | 查看学生学习行为分析、提交统计、成绩趋势图表（ECharts），支持导出成长档案 PDF |
| **课件库** | 教师上传课件（PPT/PDF/视频/文档），个人管理 + 公共课件分享市场 |
| **教学资源** | 发布教学资源到班级/小组，学生端可查看下载 |
| **班级驾驶舱** | 班级整体学情、小组表现排行、任务完成情况、评分分布 |
| **设备鉴权令牌** | 为 ESP32/ESP32-CAM/ESP32-S3/ESP32-S3 Monitor 签发设备 token，支持创建/重置/吊销/删除 |
| **病虫害诊断** | 查看 ESP32-CAM 上传的植物病虫害诊断结果（ResNet50 真实推理 5 分类），实时 WebSocket 推送 |
| **MCP 工具** | 查看小智 AI 可调用的 6 个 MCP 工具清单、调用日志，管理员可在线试用 |
| **AI 教学助手** | 基于 DeepSeek API 的对话式助手（全局悬浮按钮+右侧抽屉），双模型智能切换（chat/reasoner）、SSE 流式输出（XMLHttpRequest + onprogress，解决 ERR_ABORTED 和重复回答问题）、持久化会话历史、按角色注入系统提示词（学生学习助手 / 教师教学助手）、页面上下文感知、每日 50 次配额（独立计数，删除会话不重置；API 调用失败自动回退配额；失败时自动清理空会话）、消息显示模型标签（chat/深度思考） |

### 学生端

| 模块 | 功能描述 |
|------|----------|
| **我的概览** | 头像问候、小组信息、设备状态、待办任务、最新传感器数据 |
| **我的任务** | 查看任务、提交作业（文字+图片）、查看教师评语与得分 |
| **环境数据** | 最新传感器数据、ECharts 趋势图表（6 项指标可筛选）、历史记录（WebSocket 实时推送） |
| **我的作业** | 查看所有提交记录与批阅结果 |
| **科学实验** | 查看本班科学实验、记录观察数据、查看实验结论 |
| **病虫害诊断** | 查看本组 ESP32-CAM 上传的植物诊断结果（图片+分类+置信度+建议） |
| **个人中心** | 上传头像、修改昵称、修改密码（需旧密码验证）、学习统计 |
| **学习资源** | 查看教师发布的课件、视频和文档资料，支持下载 |
| **AI 学习助手** | 同管理端 AI 助手，学生人设（「棚棚小助手」通俗语言）、独立会话隔离、配额独立计数 |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- npm 9+

### 1. 克隆项目并进入目录

```bash
cd IoT
```

### 2. 后端启动

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.\.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # macOS / Linux

# 安装依赖
pip install -r requirements.txt

# 初始化数据库（自动创建表并填充示例数据）
python -m app.scripts.init_db

# 启动 API 服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

启动后访问：
- API 文档（Swagger UI）：http://127.0.0.1:8001/docs
- 健康检查：http://127.0.0.1:8001/health

### 3. 启动 MQTT Broker（可选，IoT 设备通信）

```bash
# Windows: 从 https://mosquitto.org/download/ 下载安装
# 启动
mosquitto -v

# Linux
sudo apt install mosquitto
sudo systemctl start mosquitto
```

### 4. 硬件模拟（可选，无需物理 ESP32 设备）

```bash
# 模拟 ESP32 节点（传感器上报 + 执行器控制 + 环境联动）
python simulate_hardware.py --node-id 1 [--interval 5] [--duration 0]

# 连接到小智 AI 官方后台（需配置 MCP_ENDPOINT 和 DEVICE_TOKEN）
python mcp_bridge.py
```

> 模拟器特性：传感器数据上报（6 项指标）、执行器联动（风扇降温降湿、水泵增湿、补光灯增光）、日间变化（6:00-14:00 渐升）、MQTT 控制命令响应、设备状态心跳。

### 5. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

启动后访问：http://localhost:5173

### 5. 默认账号

| 角色 | 用户名 | 密码 | 权限 |
|:--|:--|:--|:--|
| 管理员 | admin | 见 .env 中 INIT_ADMIN_PASSWORD | 所有权限（含用户管理） |
| 教师 | teacher | Teacher123456 | 设备/班级/小组/任务/批阅/作物/规则管理 |
| 学生 | g1s1 | Student123456 | 学生端全部功能 |

> 学生账号由教师在"小组概览"页面批量创建，用户名规则为 `g{组号}s{序号}`（如 g1s2 = 1 组 2 号）。

## 配置说明

### 后端配置 (.env)

项目根目录的 `.env` 文件控制后端运行参数：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PROJECT_NAME` | Smart Greenhouse Admin API | 项目名称 |
| `API_V1_STR` | /api/v1 | API 前缀 |
| `DATABASE_URL` | mysql+pymysql://root:CHANGE_ME@localhost:3306/greenhouse?charset=utf8mb4 | MySQL 连接地址（必须通过 .env 配置） |
| `JWT_SECRET_KEY` | — | JWT 签名密钥（生产环境务必修改） |
| `JWT_ALGORITHM` | HS256 | JWT 签名算法 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 1440 | Token 过期时间（分钟，默认 24 小时） |
| `CORS_ORIGINS` | * | 跨域来源（逗号分隔） |
| `LOG_LEVEL` | INFO | 日志级别 |
| `AUTO_CREATE_DB` | true | 启动时自动创建数据库表 |
| `INIT_ADMIN_USERNAME` | admin | 初始管理员用户名 |
| `INIT_ADMIN_PASSWORD` | Admin123456 | 初始管理员密码（生产环境务必修改） |
| `INIT_SAMPLE_DATA` | true | 是否填充示例数据 |
| `MQTT_BROKER_HOST` | localhost | MQTT Broker 地址 |
| `MQTT_BROKER_PORT` | 1883 | MQTT Broker 端口 |

### 前端配置

前端通过 Vite 代理转发 API 请求，无需额外配置（`vite.config.ts` 中已配置代理规则）。

生产环境通过 `.env` 设置 `VITE_API_BASE_URL`：

```bash
VITE_API_BASE_URL=/api/v1
```

### MySQL 数据库初始化

项目默认使用 MySQL 8.0 数据库。首次使用需完成以下步骤：

```bash
# 1. 启动 MySQL 服务后，创建数据库（utf8mb4 字符集支持中文和 emoji）
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS greenhouse CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. 在 .env 文件中配置连接（修改密码和数据库名）
# DATABASE_URL=mysql+pymysql://root:你的密码@localhost:3306/greenhouse?charset=utf8mb4

# 3. 安装 pymysql 驱动（已在 requirements.txt 中）
pip install pymysql

# 4. 初始化表结构 + 种子数据
python -m app.scripts.init_db
```

> 测试环境（pytest）仍使用 SQLite 内存数据库，无需 MySQL 即可运行 `pytest tests/`。

## API 文档

API 基础路径：`/api/v1`，共 122 个端点。创建类操作返回 201，删除类操作返回 204。设备 token 鉴权的端点使用 `Authorization: Bearer <device_token>` 头。

### 认证 (Auth)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/auth/login` | 公开 | OAuth2 表单登录（`application/x-www-form-urlencoded`），返回 access_token |
| GET | `/auth/me` | 已登录 | 获取当前用户信息 |

### 用户管理 (Users)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/users` | admin | 用户列表 |
| POST | `/users` | admin | 创建用户（201） |
| PATCH | `/users/{user_id}` | admin | 更新用户信息 |

**创建用户请求体示例：**

```json
{
  "username": "new_teacher",
  "display_name": "李老师",
  "password": "Teacher123456",
  "role": "teacher",
  "is_active": true
}
```

> 密码复杂度要求：至少 8 位且同时包含字母和数字。

### 设备节点管理 (Device Nodes)

设备节点是 ESP32 板卡，每个节点下可挂载多个组件（传感器/风扇/水泵/补光灯）。

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/device-nodes` | 已登录 | 节点列表（支持 `online` 筛选） |
| POST | `/device-nodes` | admin, teacher | 创建节点（201） |
| GET | `/device-nodes/{node_id}` | 已登录 | 节点详情 |
| PATCH | `/device-nodes/{node_id}` | admin, teacher | 更新节点 |
| DELETE | `/device-nodes/{node_id}` | admin | 删除节点（204，级联删除组件） |
| GET | `/device-nodes/{node_id}/components` | 已登录 | 节点下组件列表 |
| POST | `/device-nodes/{node_id}/components` | admin, teacher | 添加组件（201） |
| PATCH | `/device-nodes/{node_id}/components/{component_id}` | admin, teacher | 更新组件 |
| POST | `/device-nodes/{node_id}/components/{component_id}/control` | admin, teacher | 控制组件状态 |
| GET | `/device-nodes/{node_id}/logs` | admin, teacher | 节点操作日志 |

**组件控制请求体示例：**

```json
{
  "action": "on",
  "message": "手动开启风扇"
}
```

**组件类型枚举值：** `fan`（风扇）、`pump`（水泵）、`light`（补光灯）、`sensor`（传感器）
**组件状态枚举值：** `on`（开启）、`off`（关闭）、`auto`（自动）

### 传感器数据 (Sensors)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/sensors/data` | admin, teacher | 上报传感器数据（201，触发规则引擎） |
| GET | `/sensors/data` | admin, teacher | 查询历史数据（支持 `node_id`、`limit`，默认 100 条） |
| GET | `/sensors/data/latest` | admin, teacher | 获取最新一条数据 |
| GET | `/sensors/data/echarts` | admin, teacher | 获取 ECharts 图表格式数据 |

**上报传感器数据示例：**

```json
{
  "node_id": 1,
  "air_temp": 26.5,
  "air_humidity": 58.0,
  "soil_humidity": 45.0,
  "light_intensity": 350.0,
  "soil_ph": 6.8,
  "co2": 600.0
}
```

### 规则控制 (Rules)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/rules` | admin, teacher | 规则列表 |
| POST | `/rules` | admin, teacher | 创建规则（201） |
| PATCH | `/rules/{rule_id}` | admin, teacher | 更新规则 |
| POST | `/rules/{rule_id}/toggle` | admin, teacher | 启用/停用规则 |
| GET | `/rules/logs` | admin, teacher | 规则触发日志 |

**创建规则请求体示例：**

```json
{
  "name": "高温自动开风扇",
  "metric": "air_temp",
  "operator": ">",
  "threshold": 30.0,
  "action_component_type": "fan",
  "action": "on",
  "enabled": true,
  "description": "空气温度超过30℃时自动开启风扇"
}
```

**规则指标枚举值：** `air_temp`、`air_humidity`、`soil_humidity`、`light_intensity`、`soil_ph`、`co2`
**比较运算符：** `>`（大于）、`>=`（大于等于）、`<`（小于）、`<=`（小于等于）

### 班级管理 (Classrooms)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/classrooms` | admin, teacher | 班级列表（支持 `teacher_id`、`subject` 筛选） |
| POST | `/classrooms` | admin, teacher | 创建班级（201） |
| GET | `/classrooms/{classroom_id}` | admin, teacher | 班级详情 |
| PATCH | `/classrooms/{classroom_id}` | admin, teacher | 更新班级 |
| DELETE | `/classrooms/{classroom_id}` | admin, teacher | 删除班级（204） |

**科目枚举值：** `labor`（劳动课）、`science`（科学课）

### 小组管理 (Groups)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/groups` | admin, teacher | 小组列表 |
| POST | `/groups` | admin, teacher | 创建小组（201，可指定 `node_id` 绑定节点） |
| GET | `/groups/{group_id}` | admin, teacher | 小组详情 |
| PATCH | `/groups/{group_id}` | admin, teacher | 更新小组 |
| DELETE | `/groups/{group_id}` | admin, teacher | 删除小组（204） |
| POST | `/groups/{group_id}/bind-node?node_id=X` | admin, teacher | 绑定设备节点 |
| POST | `/groups/{group_id}/unbind-node` | admin, teacher | 解绑设备节点 |
| GET | `/groups/{group_id}/students` | admin, teacher, student | 小组学生名单 |
| POST | `/groups/{group_id}/students/batch` | admin, teacher | 批量创建学生（201） |

**批量创建学生请求体示例：**

```json
{
  "group_id": 1,
  "count": 4,
  "password": "Student123456"
}
```

> 用户名自动生成：`g{group_id}s{seq}`（如 g1s1、g1s2...）

### 课堂任务 (Tasks)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/tasks` | admin, teacher | 任务列表（支持 `group_id` 筛选） |
| POST | `/tasks` | admin, teacher | 创建任务（201） |
| GET | `/tasks/{task_id}` | admin, teacher | 任务详情 |
| PATCH | `/tasks/{task_id}` | admin, teacher | 更新任务 |

**任务状态枚举值：** `pending`（待开始）、`in_progress`（进行中）、`done`（已完成）
**任务类型枚举值：** `observation`（观察记录）、`experiment`（实验操作）、`maintenance`（日常维护）
**科目枚举值：** `labor`（劳动课）、`science`（科学课）

### 作业提交与批阅 (Submissions)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/submissions` | admin, teacher | 提交列表（支持 `task_id`、`student_id`、`reviewed` 筛选） |
| POST | `/submissions?task_id=X` | student | 学生提交作业（201，支持重交并重置批阅状态） |
| GET | `/submissions/{submission_id}` | 提交者或 admin/teacher | 提交详情 |
| POST | `/submissions/{submission_id}/review` | admin, teacher | 批阅提交（打分 0-100 + 评语） |

**学生提交作业（`multipart/form-data`）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `content` | string（可选） | 文字说明 |
| `files` | File[]（可选） | 附件列表，最多 10 个，支持图片/pdf/ppt/doc/txt/mp4，单个 ≤ 20MB |

> 重交会重置批阅状态（score/feedback/reviewed_at/reviewed_by 置空）；未传新文件时保留已有附件。

**教师批阅请求体：**

```json
{
  "score": 90,
  "feedback": "观察细致，记录详细。"
}
```

### 学生画像 (Analytics)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/analytics/students` | admin, teacher | 学生统计列表（支持 `group_id`、`classroom_id` 筛选） |
| GET | `/analytics/students/{student_id}` | admin, teacher | 单个学生完整分析（含趋势数据） |
| GET | `/analytics/students/{student_id}/echarts` | admin, teacher | ECharts 格式提交频率 + 得分趋势 |
| GET | `/student/me/analytics` | student | 学生本人的简化统计数据 |

### 课件库 (Courseware)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/courseware/my` | admin, teacher | 我的课件列表（支持 `file_type`、`subject` 筛选） |
| GET | `/courseware/public` | admin, teacher | 公共课件库（支持 `file_type`、`subject`、`grade_level`、`search`） |
| POST | `/courseware` | admin, teacher | 上传课件（multipart，50MB 限制，ppt/pdf/mp4/doc/txt） |
| GET | `/courseware/{id}` | admin, teacher | 课件详情 |
| PATCH | `/courseware/{id}` | admin, teacher | 更新课件元数据 |
| DELETE | `/courseware/{id}` | admin, teacher | 删除课件（含文件） |
| PATCH | `/courseware/{id}/toggle-public` | admin, teacher | 切换公开/私有 |

### 教学资源 (Teaching Resources)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/resources` | admin, teacher | 资源列表（支持 `classroom_id`、`group_id`、`subject` 筛选） |
| POST | `/resources` | admin, teacher | 上传资源（multipart，50MB 限制，ppt/pdf/mp4/doc/txt） |
| GET | `/resources/{id}` | admin, teacher | 资源详情 |
| PATCH | `/resources/{id}` | admin, teacher | 更新资源元数据 |
| DELETE | `/resources/{id}` | admin, teacher | 删除资源（含文件） |
| PATCH | `/resources/{id}/publish` | admin, teacher | 切换发布/撤回 |
| GET | `/student/me/resources` | student | 学生可见的资源列表 |

### 实验管理 (Experiments) — v4.0

支持科学课的完整实验流程：创建实验 → 分配对照/实验组 → 学生记录观察 → 完成并下结论。

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/experiments` | admin, teacher | 实验列表（支持 `class_id` 筛选） |
| POST | `/experiments` | admin, teacher | 创建实验（201） |
| GET | `/experiments/{id}` | 已登录 | 实验详情 |
| PATCH | `/experiments/{id}` | admin, teacher | 更新实验（状态、结论等） |
| DELETE | `/experiments/{id}` | admin, teacher | 删除实验（204，级联删除关联数据） |
| GET | `/experiments/{id}/groups` | admin, teacher | 实验的小组分配列表 |
| POST | `/experiments/{id}/groups` | admin, teacher | 为实验分配小组（201，指定角色） |
| DELETE | `/experiments/{id}/groups/{group_id}` | admin, teacher | 移除小组（204） |
| GET | `/experiments/{id}/observations` | 已登录 | 查看观察记录（支持 `student_id` 筛选） |
| POST | `/experiments/{id}/observations` | 已登录 | 学生记录观察（201） |

**实验状态枚举值：** `ongoing`（进行中）、`completed`（已完成）
**实验角色枚举值：** `experimental`（实验组）、`control`（对照组）

### 学生端 (Student)

学生专属接口，仅查询本人所属小组的数据。

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/student/me/group` | student | 我的小组信息 |
| GET | `/student/me/tasks` | student | 我的任务列表 |
| GET | `/student/me/submissions` | student | 我的提交记录（支持 `task_id` 筛选） |
| GET | `/student/me/sensor-data` | student | 我的传感器数据（支持 `limit`，默认 50） |
| GET | `/student/me/sensor-data/latest` | student | 我的最新传感器数据 |
| GET | `/student/me/sensor-data/echarts` | student | ECharts 格式传感器数据（支持 `metrics`、`limit`） |
| POST | `/student/me/tasks/{task_id}/submit` | student | 提交作业（201） |
| PATCH | `/student/me/profile` | student | 更新昵称/头像 URL |
| PATCH | `/student/me/password` | student | 修改密码（需旧密码验证） |
| POST | `/student/me/avatar` | student | 上传头像文件（multipart，2MB 限制，jpg/png/webp） |
| GET | `/student/me/experiments` | student | 我的班级实验列表 |
| GET | `/student/me/experiments/{id}` | student | 实验详情 |
| GET | `/student/me/experiments/{id}/group` | student | 我的小组角色（对照组/实验组） |
| GET | `/student/me/experiments/{id}/observations` | student | 实验的观察记录 |
| POST | `/student/me/experiments/{id}/observations` | student | 记录观察（201） |

### 静态资源

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/avatars/{filename}` | 用户头像静态文件（FastAPI StaticFiles 挂载，无需认证） |
| GET | `/courseware-files/{filename}` | 课件静态文件（无需认证） |
| GET | `/resource-files/{filename}` | 教学资源静态文件（无需认证） |

### 作物管理 (Crops)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/crops` | admin, teacher | 作物列表（支持 `group_id` 筛选） |
| POST | `/crops` | admin, teacher | 创建作物（201） |
| GET | `/crops/{crop_id}` | admin, teacher | 作物详情 |
| PATCH | `/crops/{crop_id}` | admin, teacher | 更新作物 |

### 日志中心 (Logs)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/logs/operations` | admin | 操作审计日志 |
| GET | `/logs/device` | admin, teacher | 设备操作日志（支持 `node_id`、`component_id` 筛选） |
| GET | `/logs/rules` | admin, teacher | 规则触发日志 |

### 仪表盘 (Dashboard)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/dashboard/overview` | admin, teacher | 全局概览（节点数、在线数、规则数、任务数、最新传感器数据） |
| GET | `/dashboard/component-summary` | admin, teacher | 按组件类型聚合统计 |

### WebSocket 实时推送 — v4.0

通过 WebSocket 实现传感器数据、设备状态、组件控制的实时推送，无需前端轮询。

| 方法 | 路径 | 说明 |
|------|------|------|
| WebSocket | `/ws?token={jwt}` | 实时数据推送连接 |

**推送事件格式（JSON）：**

```json
// 新传感器数据
{ "type": "sensor_data", "data": { "id": 1, "node_id": 1, "air_temp": 25.0, "air_humidity": 60.0, ... } }

// 组件状态变更（规则触发）
{ "type": "component_status", "data": { "component_id": 1, "node_id": 1, "type": "fan", "status": "on", "triggered_by_rule": "High Temp Fan" } }

// 设备上下线
{ "type": "device_status", "data": { "node_id": 1, "online": true, "last_reported_at": "2026-07-14T12:00:00" } }

// 病虫害诊断结果（v4.1，ESP32-CAM 上传后推送）
{ "type": "pest_diagnosis", "data": { "id": 1, "group_id": 1, "node_id": 1, "image_url": "/pest-images/...", "diagnosis_result": "tomato_early_blight", "confidence": 0.87, "suggestion": "..." } }

// 通知（v4.1，规则触发/批阅完成/任务发布等场景）
{ "type": "notification", "data": { "id": 1, "title": "任务已批阅", "content": "您的提交已评分 90", "link": "/student/tasks", "is_read": false } }
```

**连接认证：** 通过 URL 查询参数 `token` 传入 JWT。教师/管理员接收所有节点数据，学生只接收自己小组节点的数据。

**心跳：** 客户端每 30 秒发送 `"ping"`，服务端回复 `"pong"`。连接断开后自动指数退避重连（1s→2s→4s→...→30s 上限）。

## 数据库表结构

| 表名 | 字段 | 说明 |
|------|------|------|
| `users` | id, username, hashed_password, role, is_active, display_name, avatar_url, group_id, created_at, updated_at | 用户账号（含学生） |
| `device_nodes` | id, name, location, online, last_reported_at, created_at, updated_at | ESP32 设备节点 |
| `components` | id, node_id, name, type, status, metric, created_at, updated_at | 节点下组件 |
| `sensor_data` | id, node_id, air_temp, air_humidity, soil_humidity, light_intensity, soil_ph, co2, recorded_at, created_at | 传感器数据（含 `node_id, recorded_at` 复合索引） |
| `rules` | id, name, metric, operator, threshold, action_component_type, action, enabled, description, created_at, updated_at | 自动控制规则 |
| `rule_logs` | id, rule_id, sensor_data_id, node_id, component_id, message, triggered_at | 规则触发日志 |
| `device_operation_logs` | id, node_id, component_id, operator_id, action, message, created_at | 设备操作日志 |
| `operation_logs` | id, user_id, action, entity_type, entity_id, detail, created_at | 操作审计日志 |
| `classes` | id, name, teacher_id, subject, created_at | 班级 |
| `groups` | id, name, class_id, node_id, created_at | 小组 |
| `class_tasks` | id, title, description, assigned_date, due_date, status, created_by, group_id, course_subject, task_type, created_at, updated_at | 课堂任务 |
| `task_submissions` | id, task_id, student_id, content, submitted_at, score, feedback, reviewed_at, reviewed_by | 学生提交与批阅（附件见 submission_files） |
| `submission_files` | id, submission_id, filename, original_name, file_url, file_size, file_type, created_at | 提交附件（多文件，级联删除） |
| `crops` | id, name, description, growth_stage, start_date, end_date, notes, group_id, created_at, updated_at | 作物档案 |
| `courseware` | id, title, description, file_type, file_url, file_size, subject, grade_level, tags, is_public, owner_id, created_at, updated_at | 课件管理（v3.4，个人库 + 公共分享） |
| `teaching_resources` | id, title, description, resource_type, file_url, file_size, subject, classroom_id, group_id, task_id, is_published, publisher_id, download_count, created_at, updated_at | 教学资源分发（v3.4，教师→学生） |
| `experiments` | id, class_id, title, hypothesis, variable_metric, start_date, end_date, status, conclusion, created_at, updated_at | 科学实验（v4.0，含假设/变量/结论） |
| `experiment_groups` | id, experiment_id, group_id, role, variable_target, created_at | 实验小组分配（v4.0，含对照/实验组角色） |
| `experiment_observations` | id, experiment_id, sensor_data_id, student_id, content, recorded_at | 学生观察记录（v4.0） |

## 角色权限矩阵

> 以下权限以后端路由 `require_roles` 实际校验为准。

| 操作 | admin | teacher | student |
|------|:-----:|:-------:|:------:|
| 仪表盘查看 | ✅ | ✅ | ❌ |
| 设备节点列表/详情 | ✅ | ✅ | ❌ |
| 设备节点创建/编辑/删除 | ✅ | ✅ | ❌ |
| 组件控制（开/关/自动） | ✅ | ✅ | ❌ |
| 传感器数据上报/查看 | ✅ | ✅ | ❌ |
| 规则查看/创建/启停 | ✅ | ✅ | ❌ |
| 班级管理 | ✅ | ✅ | ❌ |
| 小组管理 | ✅ | ✅ | ❌ |
| 批量创建学生 | ✅ | ✅ | ❌ |
| 任务管理 | ✅ | ✅ | ❌ |
| 作业批阅 | ✅ | ✅ | ❌ |
| 作物管理 | ✅ | ✅ | ❌ |
| 操作日志查看 | ✅ | ❌ | ❌ |
| 设备日志/规则日志 | ✅ | ✅ | ❌ |
| 用户管理 | ✅ | ❌ | ❌ |
| 实验管理 | ✅ | ✅ | ❌ |
| 实验小组分配 | ✅ | ✅ | ❌ |
| 观察记录查看/创建 | ✅ | ✅ | ✅ |
| 学生端（/student/me/*） | — | — | ✅ |

## 测试

项目包含完整的测试套件：单元测试、集成测试、端到端测试，共 365 项。

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/test_unit.py -v

# 运行 API 集成测试
pytest tests/test_api.py -v

# 运行端到端测试
pytest tests/test_e2e.py -v

# 生成覆盖率报告
pytest tests/ --cov=app --cov-report=html
```

### 教师端 E2E 冒烟测试

```bash
# 启动后端后运行
python scripts/smoke_test_teacher.py
```

覆盖完整教学闭环：管理员登录 → 创建班级 → 创建小组 → 绑定节点 → 批量创建学生 → 学生登录 → 提交作业 → 教师批阅 → 仪表盘统计。

## 项目结构

```
IoT/
├── app/                          # 后端应用
│   ├── core/                     # 核心模块
│   │   ├── config.py             # 配置管理（pydantic-settings，含 MQTT 配置）
│   │   ├── security.py           # JWT 认证与密码加密（bcrypt，72 字节截断保护）
│   │   ├── dependencies.py       # FastAPI 依赖注入（get_db / get_current_user / require_roles）
│   │   ├── mqtt_client.py        # MQTT 客户端（lifespan 管理，自动重连，WebSocket 桥接）
│   │   ├── websocket_manager.py  # WebSocket ConnectionManager（v4.0，线程安全广播）
│   │   ├── rate_limit.py         # 登录频率限制（内存字典，5 次失败后锁定 15 分钟）
│   │   └── logging.py            # 日志配置
│   ├── db/                       # 数据库层
│   │   ├── base.py               # SQLAlchemy 基类
│   │   └── session.py            # engine + SessionLocal（模块级单例）
│   ├── models/                   # ORM 数据模型
│   │   ├── enums.py              # 枚举类型（UserRole/ComponentType/ComponentStatus/SensorMetric/
│   │   │                         # RuleOperator/TaskStatus/CourseSubject/TaskType/ExperimentStatus/ExperimentRole）
│   │   ├── user.py               # 用户模型（含 display_name, avatar_url, group_id）
│   │   ├── device_node.py        # 设备节点模型（ESP32 板卡）
│   │   ├── component.py          # 组件模型（传感器/执行器）
│   │   ├── sensor_data.py        # 传感器数据模型（node_id，含复合索引）
│   │   ├── rule.py               # 规则模型（action_component_type）
│   │   ├── rule_log.py           # 规则日志模型（node_id, component_id）
│   │   ├── device_log.py         # 设备日志模型（node_id, component_id）
│   │   ├── operation_log.py      # 操作审计日志模型
│   │   ├── crop.py               # 作物模型
│   │   ├── class_task.py         # 课堂任务模型（group_id, course_subject, task_type）
│   │   ├── classroom.py          # 班级模型
│   │   ├── group.py              # 小组模型（class_id, node_id）
│   │   ├── task_submission.py    # 学生提交与批阅模型（含 files 关系）
│   │   ├── submission_file.py    # 提交附件模型（v3.4，一对多，级联删除）
│   │   ├── courseware.py         # 课件模型（v3.4，owner_id + is_public）
│   │   ├── teaching_resource.py  # 教学资源模型（v3.4，publisher_id + 可选班级/小组关联）
│   │   ├── experiment.py         # 实验模型（v4.0：Experiment + ExperimentGroup + ExperimentObservation）
│   │   ├── notification.py       # 通知模型（v4.1，P0-1 通知系统）
│   │   ├── device_token.py       # 设备鉴权令牌（v4.1，P0-NEW-0，esp32/esp32cam/esp32s3）
│   │   ├── pest_diagnosis.py     # 病虫害诊断（v4.1，P0-NEW-1，ESP32-CAM 上传）
│   │   ├── mcp_call_log.py       # MCP 调用日志（v4.1，P0-NEW-2，ESP32-S3 小智 AI）
│   │   ├── chat_session.py       # AI 对话会话（v4.2，DeepSeek）
│   │   ├── chat_message.py       # AI 对话消息
│   │   └── ai_quota_usage.py     # AI 每日配额计数（独立计数表）
│   ├── schemas/                  # Pydantic 请求/响应模型
│   │   ├── user.py, device_node.py, component.py, sensor_data.py, rule.py,
│   │   │   classroom.py, group.py, class_task.py, task_submission.py, crop.py,
│   │   │   dashboard.py, operation_log.py, device_log.py, rule_log.py, token.py,
│   │   │   submission_file.py, student_analytics.py, courseware.py,
│   │   │   teaching_resource.py, experiment.py, notification.py, device_token.py,
│   │   │   pest_diagnosis.py, mcp.py
│   ├── routers/                  # API 路由（22 个路由文件，122 个端点）
│   │   ├── auth.py               # 认证接口（OAuth2 表单登录）
│   │   ├── users.py              # 用户管理接口
│   │   ├── device_nodes.py       # 设备节点与组件接口
│   │   ├── sensors.py            # 传感器数据接口
│   │   ├── rules.py              # 规则控制接口
│   │   ├── classrooms.py         # 班级管理接口
│   │   ├── groups.py             # 小组管理接口
│   │   ├── tasks.py              # 课堂任务接口
│   │   ├── submissions.py        # 作业提交与批阅接口（multipart 多文件）
│   │   ├── student.py            # 学生端接口（/student/me/*）
│   │   ├── crops.py              # 作物管理接口
│   │   ├── logs.py               # 日志查询接口
│   │   ├── dashboard.py          # 仪表盘接口
│   │   ├── analytics.py          # 学生画像 + 班级驾驶舱接口（v3.4 + v4.1）
│   │   ├── courseware.py         # 课件库接口（v3.4，含所有权校验）
│   │   ├── teaching_resources.py # 教学资源接口（v3.4，含所有权校验）
│   │   ├── experiments.py        # 实验管理接口（v4.0）
│   │   ├── notifications.py      # 通知接口（v4.1，P0-1）
│   │   ├── exports.py            # 学生成长档案 PDF 导出（v4.1，P0-3）
│   │   ├── device_tokens.py      # 设备鉴权令牌接口（v4.1，P0-NEW-0）
│   │   ├── pest_diagnoses.py     # 病虫害诊断接口（v4.1，P0-NEW-1）
│   │   ├── mcp.py                # MCP 工具调用接口（v4.1，P0-NEW-2）
│   │   └── ws.py                 # WebSocket 端点（v4.0，实时事件推送）
│   ├── services/                 # 业务逻辑层（21 个 service）
│   │   ├── user_service.py, device_node_service.py, sensor_service.py,
│   │   │   rule_service.py, classroom_service.py, group_service.py,
│   │   │   task_service.py, submission_service.py, student_service.py,
│   │   │   crop_service.py, log_service.py, dashboard_service.py,
│   │   │   student_analytics_service.py, courseware_service.py,
│   │   │   teaching_resource_service.py, experiment_service.py,
│   │   │   notification_service.py, export_service.py,
│   │   │   device_token_service.py, pest_diagnosis_service.py, mcp_service.py
│   ├── scripts/
│   │   └── init_db.py            # 数据库建表 + 种子数据 + 幂等迁移（main.py 启动时调用）
│   └── main.py                   # FastAPI 入口（lifespan + 路由挂载 + 静态文件挂载）
│
├── frontend/                     # 前端应用（Vue 3 + TypeScript + Vite 5）
│   └── src/
│       ├── api/                  # API 请求封装（22 个模块）
│       │   ├── http.ts           # Axios 实例与拦截器（401 → 重定向 /login）
│       │   ├── auth.ts, users.ts, device_nodes.ts, sensors.ts, rules.ts,
│       │   │   classrooms.ts, groups.ts, tasks.ts, submissions.ts,
│       │   │   student.ts, crops.ts, logs.ts, dashboard.ts,
│       │   │   analytics.ts, courseware.ts, resources.ts, experiments.ts,
│       │   │   notifications.ts, device_tokens.ts, pest_diagnosis.ts, mcp.ts
│       ├── components/           # 通用组件
│       │   ├── StatCard.vue      # 统计数值卡片
│       │   ├── SectionCard.vue   # 内容区块卡片
│       │   ├── LineChart.vue     # ECharts 折线图（支持主题适配）
│       │   ├── NotificationBell.vue  # 通知铃铛（v4.1，WebSocket 实时通知）
│       │   ├── AiAssistant.vue   # AI 助手（悬浮按钮 + 右侧抽屉，v4.2，DeepSeek）
│       │   └── AiMessage.vue     # AI 消息气泡（marked + DOMPurify 渲染 Markdown）
│       ├── composables/
│       │   ├── useTheme.ts       # 主题切换 composable（localStorage 持久化）
│       │   ├── useWebSocket.ts   # WebSocket 单例连接管理（模块级共享，自动重连 + 30s 心跳）
│       │   └── useAI.ts          # AI 助手状态管理（会话/流式/配额，v4.2）
│       ├── layouts/
│       │   ├── AdminLayout.vue   # 管理端布局（三组导航：主菜单/教学管理/系统管理）
│       │   └── StudentLayout.vue # 学生端布局
│       ├── router/
│       │   └── index.ts          # 路由配置与导航守卫（区分管理端/学生端）
│       ├── stores/
│       │   └── auth.ts           # Pinia 认证状态
│       ├── views/                # 管理端页面
│       │   ├── LoginView.vue     # 登录页
│       │   ├── DashboardView.vue # 仪表盘（教学视角）
│       │   ├── DevicesView.vue   # 设备节点管理（含设备鉴权令牌管理，v4.1）
│       │   ├── SensorsView.vue   # 传感器数据
│       │   ├── RulesView.vue     # 规则控制
│       │   ├── ClassroomsView.vue # 班级管理
│       │   ├── GroupsView.vue    # 小组概览
│       │   ├── TasksView.vue     # 课堂任务
│       │   ├── GradingView.vue   # 批阅中心
│       │   ├── CropsView.vue     # 作物管理
│       │   ├── LogsView.vue      # 日志中心
│       │   ├── UsersView.vue     # 用户权限
│       │   ├── StudentAnalyticsView.vue  # 学生画像（v3.4，含 PDF 导出 v4.1）
│       │   ├── CoursewareView.vue        # 课件库（v3.4）
│       │   ├── ResourcesView.vue         # 教学资源（v3.4）
│       │   ├── ExperimentsView.vue       # 实验管理（v4.0）
│       │   ├── ClassroomDashboardView.vue # 班级驾驶舱（v4.1，P0-2）
│       │   ├── PestDiagnosisView.vue     # 病虫害诊断（v4.1，P0-NEW-1）
│       │   ├── McpToolsView.vue          # MCP 工具管理（v4.1，P0-NEW-2）
│       │   └── student/          # 学生端页面
│       │       ├── StudentDashboardView.vue   # 学生仪表盘
│       │       ├── StudentTasksView.vue       # 我的任务
│       │       ├── StudentSensorView.vue      # 环境数据（含 ECharts 图表）
│       │       ├── StudentSubmissionsView.vue # 我的作业
│       │       ├── StudentProfileView.vue     # 个人中心（头像/昵称/密码/统计）
│       │       ├── StudentResourcesView.vue   # 学习资源（v3.4）
│       │       ├── StudentExperimentsView.vue # 科学实验（v4.0）
│       │       └── StudentPestDiagnosisView.vue # 病虫害诊断（v4.1）
│       ├── App.vue               # 根组件
│       ├── main.ts               # 应用入口
│       ├── styles.css            # 全局样式 + 主题变量（烛光手记 / 羊皮纸）
│       └── types.ts              # TypeScript 类型定义
│
├── scripts/                      # 工具脚本
│   └── smoke_test_teacher.py     # 教师端 E2E 冒烟测试（19 项）
├── tests/                        # 测试套件（365 项，含设备鉴权+病虫害诊断+MCP+AI 助手）
│   ├── conftest.py               # pytest 公共配置（含 student_token fixture）
│   ├── test_unit.py              # 单元测试（Schema/枚举）
│   ├── test_api.py               # API 集成测试
│   └── test_e2e.py               # 端到端流程测试
│
├── data/                         # 数据目录（文件上传存储，数据库由 MySQL 管理）
│   ├── avatars/                  # 用户头像（2MB，jpg/png/webp）
│   ├── courseware/               # 课件文件（50MB，ppt/pdf/mp4/doc/txt）
│   ├── resources/                # 教学资源文件（50MB）
│   ├── submissions/              # 学生作业附件（20MB，最多 10 个）
│   └── pest-images/              # 病虫害诊断图片（v4.1，ESP32-CAM 上传）
├── .env                          # 环境变量配置
├── .env.example                  # 环境变量示例
├── requirements.txt              # Python 依赖
└── simulate_hardware.py          # 硬件模拟器（ESP32 传感器/执行器模拟，MQTT 通信）
```

## 常见问题

### Q: 启动报错 `ModuleNotFoundError: No module named 'app'`

确保在项目根目录 (`IoT/`) 下运行命令，且已激活虚拟环境。

### Q: 前端页面空白或 API 请求 404

确认后端已启动（`http://127.0.0.1:8001/health` 返回 `{"status":"ok"}`），前端 Vite 代理会自动转发 `/api` 请求到后端。

### Q: 登录失败

- 登录接口使用 OAuth2 表单格式（`application/x-www-form-urlencoded`），不是 JSON。
- 确认数据库已初始化（`python -m app.scripts.init_db`），默认账号见上方表格。
- 登录有频率限制：5 次失败后锁定 15 分钟。
- 如密码被修改或忘记，可删除 `data/greenhouse.db` 后重新初始化。

### Q: bcrypt 报错

某些环境下 bcrypt 5.x 与 passlib 存在兼容性问题。如遇此问题，降级 bcrypt：

```bash
pip install bcrypt==4.0.1
```

### Q: `simulate_hardware.py` 运行报错

确保已启动后端（`uvicorn app.main:app --host 0.0.0.0 --port 8001`）和 MQTT broker（`mosquitto -v`）。模拟器会自动从数据库读取节点配置和设备 token。

模拟器参数说明：
- `--node-id`：节点 ID（默认 1），对应数据库中 DeviceNode 的 id
- `--interval`：传感器上报间隔秒数（默认 5）
- `--duration`：运行时长秒数，0 表示无限运行（默认 0）
- `--mqtt-host` / `--mqtt-port`：MQTT broker 地址（默认 localhost:1883）

### Q: 如何切换数据库

修改 `.env` 中的 `DATABASE_URL`，然后重新运行 `python -m app.scripts.init_db`。项目默认使用 MySQL 8.0，如需切换到其他数据库（如 PostgreSQL），安装对应驱动并修改连接串即可。

### Q: 如何添加新的传感器指标

1. 在 `app/models/enums.py` 的 `SensorMetric` 枚举中添加新值
2. 在 `app/models/sensor_data.py` 中添加对应字段
3. 在 `app/schemas/sensor_data.py` 中添加对应字段
4. 在 `app/services/sensor_service.py` 中更新数据处理逻辑
5. 前端 `types.ts` 中更新 `SensorData` 接口
6. 更新前端页面模板中的表单和表格列

### Q: 生产环境部署建议

1. 修改 `.env` 中的 `JWT_SECRET_KEY` 为强随机字符串
2. 将 `CORS_ORIGINS` 设置为具体的前端域名
3. 配置 MySQL 连接池参数（`pool_recycle` 避免 8 小时空闲断开）
4. 使用 Nginx 反向代理，前端静态文件直接由 Nginx 提供服务
5. 使用 Gunicorn + Uvicorn workers 运行后端

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001
```

## 主题切换

前端支持深色/浅色两种主题模式，主题偏好自动保存到 localStorage。

- **切换方式**：侧边栏底部主题切换按钮
- **深色主题**：默认主题，烛光手记风格（暖琥珀 + 烛光金绿，如夜晚烛光下翻阅的旧手记）
- **浅色主题**：羊皮纸 / 田野手记风格（暖大地色调，明亮柔和，高对比度文本）
- **切换动画**：0.35s 平滑过渡
- **ECharts 适配**：图表配色随主题自动切换
- **防闪烁**：页面加载时通过内联脚本立即应用已保存的主题
