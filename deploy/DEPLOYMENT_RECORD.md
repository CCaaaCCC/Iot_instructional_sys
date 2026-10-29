# 部署记录（阿里云 47.80.57.231）

本文件记录本次生产部署的实际参数与验证结果。**不包含任何明文密码**，凭据位置见文末。

## 基本信息

| 项 | 值 |
|----|----|
| 部署日期 | 2026-10-28 |
| 服务器 | 阿里云 ECS `47.80.57.231` |
| 操作系统 | Ubuntu 24.04.5 LTS |
| 规格 | 2 核 / 1.6 GiB 可用内存 / 8 GiB swap / 40 GB 磁盘 |
| 访问地址 | **http://47.80.57.231:8080** |
| 项目目录 | `/opt/greenhouse` |
| 运行账号 | `greenhouse`（系统账号，nologin） |
| 部署方式 | `deploy/install.sh` |
| 部署参数 | `SERVER_IP=47.80.57.231 HTTP_PORT=8080 ENABLE_UFW=0 ENABLE_MCP=0 INIT_SAMPLE_DATA=false` |

## 端口与服务

| 端口 | 监听地址 | 用途 | 说明 |
|------|---------|------|------|
| 80 | Docker `gravity-frontend` | 原有 `gravity_tunnel` 项目 | **未改动** |
| 8080 | 0.0.0.0（Nginx） | 大棚平台网页 + API/WebSocket 反向代理 | 安全组已放行 |
| 8001 | 127.0.0.1（uvicorn） | 后端 API，仅本机 | 不对外 |
| 1883 | 0.0.0.0（Mosquitto） | MQTT，用户名/密码认证 | 安全组已放行 |
| 3306 | 127.0.0.1（MySQL） | 数据库，仅本机 | 不对外 |

systemd 服务：`mysql`、`nginx`、`mosquitto`、`greenhouse-api` 均为 active。`greenhouse-mcp` 未启用。

## 部署架构

```
公网 :8080 ── Nginx ──┬─ /              → /var/www/greenhouse
                      ├─ /api /ws /health → 127.0.0.1:8001
                      └─ /avatars 等     → 127.0.0.1:8001
ESP32 设备 ── 公网 :1883 ── Mosquitto（密码认证）
后端 ── 127.0.0.1:3306 ── MySQL 8（宿主机）
```

## 数据迁移

| 项 | 迁移前（本地） | 迁移后（服务器） |
|----|---------------|-----------------|
| 表数量 | 26 | 26 |
| 用户 | 16 | 16 |
| 传感器数据 | 7661 | 7661 |
| 课堂任务 | 8 | 8 |
| 作业提交 | 7 | 7 |
| 病虫害记录 | 2 | 2 |
| 上传文件 | 267 | 267 |

- 迁移方式：本地 `mysqldump` → 上传 → 停止 `greenhouse-api` → `mysql greenhouse < dump.sql` → 启动。
- 导入后账号仍为原库账号，**登录密码以原数据库为准**，请在登录后立即修改。

## 验证结果

| 验证项 | 结果 |
|--------|------|
| 外网页面 `http://47.80.57.231:8080` | HTTP 200 |
| `/health` | `{"status":"ok","mqtt":"connected"}` |
| 后端 MQTT 日志 | `MQTT auth enabled, username=greenhouse`，已连接并订阅 |
| MQTT 匿名连接 | 被拒绝，`rc=135 Not authorized` |
| Mosquitto 密码文件 | `/etc/mosquitto/passwd`，`mosquitto:mosquitto`，600 |
| 前端静态文件 | `/var/www/greenhouse`，Vue history 路由正常 |
| 数据文件 | `/opt/greenhouse/data`，267 个 |

## 关键配置位置

| 内容 | 路径 |
|------|------|
| 后端环境变量 | `/opt/greenhouse/.env`（权限 600） |
| Nginx 站点 | `/etc/nginx/sites-available/greenhouse` |
| 后端服务 | `/etc/systemd/system/greenhouse-api.service` |
| MCP 服务 | `/etc/systemd/system/greenhouse-mcp.service` |
| Mosquitto 配置 | `/etc/mosquitto/conf.d/greenhouse.conf` |
| Mosquitto 密码文件 | `/etc/mosquitto/passwd` |
| 前端静态文件 | `/var/www/greenhouse` |
| 上传文件 | `/opt/greenhouse/data` |

## 凭据位置（不记录明文）

- 管理员账号：`admin`，密码为**原数据库密码**（导入时保留），登录后请修改。
- MQTT 用户名：`greenhouse`；密码见 `/opt/greenhouse/.env` 与 `/etc/mosquitto/passwd`。
- 数据库密码：见 `/opt/greenhouse/.env`。
- 切勿把 `.env`、`/etc/mosquitto/passwd` 或数据库 dump 提交到仓库或发到公开渠道。

## 本次未启用 / 未改动

- **MCP 小智桥接**：未启用。需要时执行 `systemctl enable --now greenhouse-mcp`。
- **UFW**：未启用。宿主机 80 被 Docker 占用，为避免影响现有容器，防火墙统一交给阿里云安全组。
- **gravity_tunnel**：未改动，仍占用 80 端口。
- **PyTorch**：未安装。病虫害图片上传会返回“PyTorch 未安装”，其余功能正常。

## 运维命令

```bash
systemctl status greenhouse-api
journalctl -u greenhouse-api -f
nginx -t && systemctl reload nginx
tail -f /var/log/nginx/access.log

# 数据库备份
mysqldump -u greenhouse -p greenhouse > /root/greenhouse-$(date +%F).sql
```

## 后续建议

1. 修改服务器 root 密码（部署期间曾使用密码登录）。
2. 登录平台后立即修改 admin 密码。
3. 安全组建议把 1883 收敛到学校出口 IP。
4. 正式使用建议增加域名和 HTTPS。
5. 定期备份数据库与 `/opt/greenhouse/data`。
6. 如需启用病虫害识别：安装 torch/torchvision，上传 `pest_model.pth`，并调高 `greenhouse-api.service` 的 `MemoryMax`。
