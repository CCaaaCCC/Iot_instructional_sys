# 智慧大棚教学平台部署指南（阿里云 Ubuntu 2 核 2G）

本目录提供一套面向 **Ubuntu 22.04 / 24.04 + 2 核 2G + 公网 IP + 云端 MQTT** 的部署文件。部署后由 Nginx 同时提供前端静态页面和 API 反向代理，后端以 systemd 托管，MySQL、Mosquitto 与本机同装。

## 本次部署实例

| 项 | 值 |
|----|----|
| 访问地址 | **http://xxxxxxxxxx** |
| 服务器 | 阿里云 ECS，Ubuntu 24.04.5 LTS，2 核 / 1.6 GiB / 8 GiB swap |
| Nginx 端口 | `8080`（80 被 Docker 项目 `gravity_tunnel` 占用，未改动） |
| 部署参数 | `HTTP_PORT=8080 ENABLE_UFW=0 ENABLE_MCP=0 INIT_SAMPLE_DATA=false` |
| MQTT | `47.80.57.231:1883`，用户名/密码认证 |
| 详细记录 | [DEPLOYMENT_RECORD.md](DEPLOYMENT_RECORD.md) |

## 目录结构

```
deploy/
├── README.md                       # 本文档
├── DEPLOYMENT_RECORD.md            # 本次服务器部署记录（不含密码）
├── install.sh                      # 一键安装脚本（root 执行）
├── env.production.example          # .env 生产模板
├── nginx/greenhouse.conf           # Nginx 站点配置
├── mosquitto/greenhouse.conf       # Mosquitto 云端 Broker 配置
└── systemd/
    ├── greenhouse-api.service      # 后端 API 服务
    └── greenhouse-mcp.service      # 小智 AI MCP 桥接（可选）
```

> `nginx/greenhouse.conf` 中的 `__HTTP_PORT__`、`__WEB_ROOT__` 和 systemd unit 中的 `__APP_DIR__`、`__APP_USER__` 都是占位符，由 `install.sh` 安装时替换，不需要手动改。

## 部署架构

```
公网 IP:8080  ── Nginx ──┬─ /                → /var/www/greenhouse（Vue dist）
                         ├─ /api /ws /health → 127.0.0.1:8001（uvicorn，1 worker）
                         └─ /avatars 等上传目录 → 127.0.0.1:8001
ESP32 设备 ── 公网 IP:1883 ── Mosquitto（用户名/密码认证）
后端 ── 127.0.0.1:3306 ── MySQL
```

> 默认 `HTTP_PORT=80`；如果 80 已被其他服务（例如 Docker）占用，用 `HTTP_PORT=8080` 部署。本次实例即采用 8080。

资源取舍：**不安装 PyTorch/torchvision**（省约 1.5G 磁盘和大量内存），因此 ESP32-CAM 图片诊断上传会返回“PyTorch 未安装”，其余功能不受影响。

---

## 一、部署前提

### 1. 阿里云安全组

| 端口 | 来源 | 用途 |
|------|------|------|
| 22 | 你的固定 IP | SSH |
| 8080 | 0.0.0.0/0 | 网页访问（若用默认 80 则改为 80） |
| 1883 | 0.0.0.0/0 或学校出口 IP | 硬件 MQTT |

不要开放 8001、3306。

### 2. 本地准备

- Windows PowerShell（自带 `tar`、`ssh`、`scp`）
- Node.js（本地构建前端，避免 2G 服务器构建时 OOM）

---

## 二、首次部署

### 1. 本地构建前端

```powershell
cd d:\IoT\frontend
npm run build
```

### 2. 打包并上传

```powershell
cd d:\IoT
tar -czf greenhouse.tar.gz `
  --exclude=node_modules `
  --exclude=.venv `
  --exclude=.git `
  --exclude=*.pth `
  --exclude=__pycache__ `
  --exclude=.pytest_cache `
  --exclude=*.db `
  --exclude=*.log `
  --exclude=*.pid `
  .
scp greenhouse.tar.gz root@47.80.57.231:/tmp/
```

> 只排除模型权重 `*.pth`（约 94 MB），**不要**使用 `--exclude=models`，否则会把 `app/models` 代码目录一起排除，导致 `ModuleNotFoundError: No module named 'app.models'`。
> `frontend/dist`、`data/`、`.env` 会随包上传；`install.sh` 会自动复制前端并保留 DeepSeek / MCP 密钥。

### 3. 服务器解压

```bash
sudo mkdir -p /opt/greenhouse
sudo tar -xzf /tmp/greenhouse.tar.gz -C /opt/greenhouse
```

### 4. 执行安装

```bash
sudo SERVER_IP=47.80.57.231 HTTP_PORT=8080 ENABLE_UFW=0 \
     MQTT_ALLOWED_IP=0.0.0.0/0 \
     bash /opt/greenhouse/deploy/install.sh
```

脚本会完成：系统依赖、2G swap、MySQL 建库建号与调优、`.env` 生成、Python venv（跳过 torch）、数据库初始化、systemd 服务、Nginx、Mosquitto、前端静态文件部署；`ENABLE_UFW=1` 时还会配置 ufw。

执行结束会打印 **随机生成的管理员密码、数据库密码和 MQTT 账号密码**，请立即保存。

> MQTT 采用「用户名 + 密码」认证。`install.sh` 会创建 `/etc/mosquitto/passwd`，并把同一组账号写入后端 `.env`。上位机固件需要填入相同凭据后重新烧录，详见下方「MQTT 认证配置」。

### 5. 安装脚本可选变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_DIR` | 脚本上级目录 | 项目路径，默认 `/opt/greenhouse` |
| `APP_USER` | `greenhouse` | 运行账号 |
| `WEB_ROOT` | `/var/www/greenhouse` | 前端静态目录 |
| `HTTP_PORT` | `80` | Nginx 监听端口；80 被占用时改成 8080 |
| `ENABLE_UFW` | `1` | 是否启用并配置 ufw；Docker 占 80 时建议设 `0` |
| `SERVER_IP` | 自动探测 | 写入 `CORS_ORIGINS` |
| `MQTT_ALLOWED_IP` | 空 | 放行 1883 的来源 IP |
| `MQTT_USERNAME` | `greenhouse` | MQTT 用户名 |
| `MQTT_PASSWORD` | 随机生成 | MQTT 密码，需同步到固件 |
| `DB_PASSWORD` | 随机生成 | MySQL 密码 |
| `ADMIN_PASSWORD` | 随机生成 | 管理员初始密码 |
| `JWT_SECRET` | 随机生成 | JWT 密钥 |
| `INIT_SAMPLE_DATA` | `false` | 是否写入演示数据 |
| `ENABLE_MCP` | `auto` | `auto`/`1`/`0`，是否启用小智 AI 桥接 |

示例（演示环境，带示例数据）：

```bash
sudo SERVER_IP=47.80.57.231 MQTT_ALLOWED_IP=5.6.7.8 INIT_SAMPLE_DATA=true \
     bash /opt/greenhouse/deploy/install.sh
```

若 80 端口已被其他服务占用（例如 Docker 容器），用非标准端口部署：

```bash
sudo SERVER_IP=47.80.57.231 HTTP_PORT=8080 ENABLE_UFW=0 \
     MQTT_ALLOWED_IP=0.0.0.0/0 bash /opt/greenhouse/deploy/install.sh
```

此时访问地址为 `http://47.80.57.231:8080`，并需在阿里云安全组放行 8080 和 1883。

若启用演示数据，`teacher/Teacher123456`、`g1s1/Student123456` 等弱口令账号会被创建，公网环境请在登录后立即修改密码。

### 6. 数据迁移（从旧环境导入）

1. 本地导出数据库（Windows PowerShell，执行后会提示输入原 MySQL 密码）：

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe" -uroot -p `
  --default-character-set=utf8mb4 --single-transaction --routines --triggers `
  --no-tablespaces --result-file=D:\greenhouse.sql greenhouse
```

2. 上传到服务器：

```powershell
scp D:\greenhouse.sql root@47.80.57.231:/tmp/
```

3. 服务器导入（先停后端，避免导表期间连接冲突）：

```bash
sudo systemctl stop greenhouse-api
sudo mysql --default-character-set=utf8mb4 greenhouse < /tmp/greenhouse.sql
sudo systemctl start greenhouse-api
```

4. 校验：

```bash
sudo mysql -N -e "SELECT COUNT(*) FROM greenhouse.users;"
sudo mysql -N -e "SELECT COUNT(*) FROM greenhouse.sensor_data;"
find /opt/greenhouse/data -type f | wc -l
```

> 导入后**账号密码以旧库为准**，安装脚本随机生成的管理员密码会失效。
> `data/` 上传文件随部署包一起上传；如单独迁移，解压后执行 `chown -R greenhouse:greenhouse /opt/greenhouse/data`。

---

## 三、部署后验证

```bash
# 后端
curl http://127.0.0.1:8001/health

# 经 Nginx
curl http://47.80.57.231:8080/health
curl -X POST http://47.80.57.231:8080/api/v1/auth/login \
     -d 'username=admin&password=<管理员密码>'

# MQTT（需认证）
mosquitto_pub -h 127.0.0.1 -u greenhouse -P '<MQTT密码>' \
  -t greenhouse/sensor/data -m '{"node_id":1,"air_temp":26.5}'
```

浏览器访问 `http://47.80.57.231:8080`：

1. 用 admin 登录；
2. 页面右下角 WebSocket 应显示已连接；
3. 设备页能看到模拟上报数据（可运行 `simulate_hardware.py`）。

### MQTT 认证配置

服务器侧（`install.sh` 已自动完成）：

```bash
mosquitto_passwd -c -b /etc/mosquitto/passwd greenhouse '<MQTT密码>'
chown mosquitto:mosquitto /etc/mosquitto/passwd
chmod 600 /etc/mosquitto/passwd
systemctl restart mosquitto
```

固件侧：修改 `tft_screen_1.9/src/wifi_config.h`：

```cpp
#define MQTT_BROKER_HOST "47.80.57.231"
#define MQTT_BROKER_PORT 1883
#define MQTT_USERNAME    "greenhouse"
#define MQTT_PASSWORD    "<服务器 .env 中的 MQTT_PASSWORD>"
```

`NODE_ID` 与平台设备节点 id 保持一致，然后重新烧录。

后端侧：`.env` 中同名变量由安装脚本写入，修改密码后重启：

```bash
sudo systemctl restart greenhouse-api
```

---

## 四、日常更新

### 只更新前端

```powershell
cd d:\IoT\frontend
npm run build
scp -r dist\* root@47.80.57.231:/var/www/greenhouse/
```

### 更新后端

```powershell
cd d:\IoT
tar -czf greenhouse.tar.gz --exclude=node_modules --exclude=.venv --exclude=.git --exclude=*.pth --exclude=__pycache__ .
scp greenhouse.tar.gz root@47.80.57.231:/tmp/
```

```bash
sudo tar -xzf /tmp/greenhouse.tar.gz -C /opt/greenhouse
sudo chown -R greenhouse:greenhouse /opt/greenhouse
sudo -u greenhouse /opt/greenhouse/.venv/bin/pip install \
     -r /tmp/greenhouse-requirements.txt
sudo systemctl restart greenhouse-api
```

> 依赖有变化时重新生成 `/tmp/greenhouse-requirements.txt`：
> `grep -vE '^(torch|torchvision)' /opt/greenhouse/requirements.txt > /tmp/greenhouse-requirements.txt`

### 查看日志

```bash
journalctl -u greenhouse-api -f
journalctl -u greenhouse-mcp -f
tail -f /var/log/nginx/access.log
```

---

## 五、常见问题

**502 Bad Gateway**
```bash
systemctl status greenhouse-api
journalctl -u greenhouse-api -n 100
```
多为依赖缺失或 `.env` 中数据库密码不一致。

**WebSocket 连不上**
确认 Nginx 的 `/ws` 配置包含 `Upgrade` / `Connection "upgrade"`，且安全组放行实际 HTTP 端口（本次为 8080）；`4001/4003` 为 token 失效，重新登录。

**80 端口被占用导致 Nginx 起不来**
```bash
ss -tlnp | grep ':80 '
```
若被 Docker 等占用，改用 `HTTP_PORT=8080` 部署，并在安全组放行 8080。

**上传文件 413**
Nginx `client_max_body_size` 默认已设为 60m；如仍不足，修改后 `nginx -t && systemctl reload nginx`。

**内存不足 / 服务被 OOM Kill**
```bash
free -h
swapon --show
journalctl -k | grep -i oom
```
确认 2G swap 已启用、`greenhouse-api` 只有 1 个 worker、MySQL `performance_schema=OFF`。

**Mosquitto 启动失败**
```bash
systemctl status mosquitto
grep -n 'listener' /etc/mosquitto/mosquitto.conf
```
若主配置存在未注释的 `listener 1883`，与 `conf.d/greenhouse.conf` 冲突，注释掉主配置中的那一行。

**MQTT 认证失败（reason_code=5 / Not authorized）**
```bash
# 确认密码文件存在且权限正确
ls -l /etc/mosquitto/passwd
# 用命令行验证凭据
mosquitto_pub -h 127.0.0.1 -u greenhouse -P '<MQTT密码>' \
  -t test/auth -m ok
```
后端日志出现 `MQTT connection failed, reason_code=5` 时，检查 `.env` 的 `MQTT_USERNAME` / `MQTT_PASSWORD` 是否与密码文件一致；固件连不上时检查 `wifi_config.h` 是否已填入相同凭据并重新烧录。

**病虫害上传失败**
预期行为：服务器未安装 PyTorch。如需启用，见下方“启用病虫害模型”。

---

## 六、安全须知

1. **1883 仍建议限制来源 IP**。虽然已启用用户名/密码认证，但限制来源可减少暴力破解和扫描风险。
2. **HTTP 明文**：JWT 和密码在公网可被嗅探，仅建议短期演示；正式使用请加域名和 HTTPS。
3. `.env` 权限为 `600`，包含数据库密码、JWT 密钥、MQTT 密码、DeepSeek Key、小智设备令牌，切勿外传。
4. 定期备份数据库：
   ```bash
   mysqldump -u greenhouse -p greenhouse > /root/greenhouse-$(date +%F).sql
   ```
5. 全新部署请使用安装脚本随机生成的管理员密码，不要沿用 `Admin123456`；**导入旧库后管理员密码以旧库为准**，登录后立即修改。

---

## 七、可选：启用病虫害模型（需要更多内存）

2 核 2G 不建议。若必须启用：

```bash
sudo -u greenhouse /opt/greenhouse/.venv/bin/pip install torch torchvision \
  --index-url https://download.pytorch.org/whl/cpu
# 上传训练产物到 /opt/greenhouse/models/pest_model.pth
sudo systemctl restart greenhouse-api
```

需同时把 `greenhouse-api.service` 的 `MemoryMax` 调高，并关注 OOM。
