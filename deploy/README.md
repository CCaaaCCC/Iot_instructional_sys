# 智慧大棚教学平台部署指南（阿里云 Ubuntu 2 核 2G）

本目录提供一套面向 **Ubuntu 22.04 / 24.04 + 2 核 2G + 公网 IP + 云端 MQTT** 的部署文件。部署后由 Nginx 同时提供前端静态页面和 API 反向代理，后端以 systemd 托管，MySQL、Mosquitto 与本机同装。

## 目录结构

```
deploy/
├── README.md                       # 本文档
├── install.sh                      # 一键安装脚本（root 执行）
├── env.production.example          # .env 生产模板
├── nginx/greenhouse.conf           # Nginx 站点配置
├── mosquitto/greenhouse.conf       # Mosquitto 云端 Broker 配置
└── systemd/
    ├── greenhouse-api.service      # 后端 API 服务
    └── greenhouse-mcp.service      # 小智 AI MCP 桥接（可选）
```

## 部署架构

```
公网 IP:80  ── Nginx ──┬─ /                → /var/www/greenhouse（Vue dist）
                       ├─ /api /ws /health → 127.0.0.1:8001（uvicorn，1 worker）
                       └─ /avatars 等上传目录 → 127.0.0.1:8001
ESP32 设备 ── 公网 IP:1883 ── Mosquitto
后端 ── 127.0.0.1:3306 ── MySQL
```

资源取舍：**不安装 PyTorch/torchvision**（省约 1.5G 磁盘和大量内存），因此 ESP32-CAM 图片诊断上传会返回“PyTorch 未安装”，其余功能不受影响。

---

## 一、部署前提

### 1. 阿里云安全组

| 端口 | 来源 | 用途 |
|------|------|------|
| 22 | 你的固定 IP | SSH |
| 80 | 0.0.0.0/0 | 网页访问 |
| 1883 | **仅学校出口公网 IP** | 硬件 MQTT |

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
  --exclude=models `
  --exclude=data `
  .
scp greenhouse.tar.gz root@<服务器IP>:/tmp/
```

> `frontend/dist` 会随包上传，`install.sh` 会自动复制到 `/var/www/greenhouse`；`.env` 也会上传，脚本会保留其中的 DeepSeek / MCP 密钥并覆盖部署相关项。

### 3. 服务器解压

```bash
sudo mkdir -p /opt/greenhouse
sudo tar -xzf /tmp/greenhouse.tar.gz -C /opt/greenhouse
```

### 4. 执行安装

```bash
sudo SERVER_IP=<服务器公网IP> \
     MQTT_ALLOWED_IP=<学校出口IP> \
     bash /opt/greenhouse/deploy/install.sh
```

脚本会完成：系统依赖、2G swap、MySQL 建库建号与调优、`.env` 生成、Python venv（跳过 torch）、数据库初始化、systemd 服务、Nginx、Mosquitto、ufw 和前端静态文件部署。

执行结束会打印 **随机生成的管理员密码和数据库密码**，请立即保存。

### 5. 安装脚本可选变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_DIR` | 脚本上级目录 | 项目路径，默认 `/opt/greenhouse` |
| `APP_USER` | `greenhouse` | 运行账号 |
| `WEB_ROOT` | `/var/www/greenhouse` | 前端静态目录 |
| `SERVER_IP` | 自动探测 | 写入 `CORS_ORIGINS` |
| `MQTT_ALLOWED_IP` | 空 | 放行 1883 的来源 IP |
| `DB_PASSWORD` | 随机生成 | MySQL 密码 |
| `ADMIN_PASSWORD` | 随机生成 | 管理员初始密码 |
| `JWT_SECRET` | 随机生成 | JWT 密钥 |
| `INIT_SAMPLE_DATA` | `false` | 是否写入演示数据 |
| `ENABLE_MCP` | `auto` | `auto`/`1`/`0`，是否启用小智 AI 桥接 |

示例（演示环境，带示例数据）：

```bash
sudo SERVER_IP=1.2.3.4 MQTT_ALLOWED_IP=5.6.7.8 INIT_SAMPLE_DATA=true \
     bash /opt/greenhouse/deploy/install.sh
```

若启用演示数据，`teacher/Teacher123456`、`g1s1/Student123456` 等弱口令账号会被创建，公网环境请在登录后立即修改密码。

---

## 三、部署后验证

```bash
# 后端
curl http://127.0.0.1:8001/health

# 经 Nginx
curl http://<服务器IP>/health
curl -X POST http://<服务器IP>/api/v1/auth/login \
     -d 'username=admin&password=<管理员密码>'

# MQTT
mosquitto_pub -h 127.0.0.1 -t greenhouse/sensor/data \
  -m '{"node_id":1,"air_temp":26.5}'
```

浏览器访问 `http://<服务器IP>`：

1. 用 admin 登录；
2. 页面右下角 WebSocket 应显示已连接；
3. 设备页能看到模拟上报数据（可运行 `simulate_hardware.py`）。

硬件侧：修改 `tft_screen_1.9/src/wifi_config.h` 的 `MQTT_BROKER_HOST` 为服务器公网 IP，`NODE_ID` 与平台设备节点 id 一致，重新烧录。

---

## 四、日常更新

### 只更新前端

```powershell
cd d:\IoT\frontend
npm run build
scp -r dist\* root@<服务器IP>:/var/www/greenhouse/
```

### 更新后端

```powershell
cd d:\IoT
tar -czf greenhouse.tar.gz --exclude=node_modules --exclude=.venv --exclude=.git --exclude=models --exclude=data .
scp greenhouse.tar.gz root@<服务器IP>:/tmp/
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
确认 Nginx 的 `/ws` 配置包含 `Upgrade` / `Connection "upgrade"`，且安全组放行 80；`4001/4003` 为 token 失效，重新登录。

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

**病虫害上传失败**
预期行为：服务器未安装 PyTorch。如需启用，见下方“启用病虫害模型”。

---

## 六、安全须知

1. **1883 必须限制来源 IP**。当前固件匿名连接 MQTT，公开暴露可被任意伪造数据或控制执行器。
2. **HTTP 明文**：JWT 和密码在公网可被嗅探，仅建议短期演示；正式使用请加域名和 HTTPS。
3. `.env` 权限为 `600`，包含数据库密码、JWT 密钥、DeepSeek Key、小智设备令牌，切勿外传。
4. 定期备份数据库：
   ```bash
   mysqldump -u greenhouse -p greenhouse > /root/greenhouse-$(date +%F).sql
   ```
5. 管理员密码使用安装脚本随机生成值，不要沿用 `Admin123456`。

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
