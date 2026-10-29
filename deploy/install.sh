#!/usr/bin/env bash
# ============================================================
# 智慧大棚教学平台 - Ubuntu 22.04/24.04 一键部署脚本
#
# 用法（在服务器上以 root 执行）:
#   sudo bash /opt/greenhouse/deploy/install.sh
#
# 可选环境变量:
#   APP_DIR=/opt/greenhouse          项目目录（默认取脚本上级目录）
#   APP_USER=greenhouse              运行账号
#   WEB_ROOT=/var/www/greenhouse     Nginx 静态文件目录
#   SERVER_IP=1.2.3.4                公网 IP（默认自动探测）
#   MQTT_ALLOWED_IP=5.6.7.8          允许访问 1883 的学校出口 IP
#   DB_PASSWORD=...                  MySQL 密码（默认随机生成）
#   ADMIN_PASSWORD=...               管理员初始密码（默认随机生成）
#   JWT_SECRET=...                   JWT 密钥（默认随机生成）
#   INIT_SAMPLE_DATA=false           是否写入演示数据
#   ENABLE_MCP=auto                  auto/1/0，是否启用小智 AI 桥接
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${APP_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
APP_USER="${APP_USER:-greenhouse}"
WEB_ROOT="${WEB_ROOT:-/var/www/greenhouse}"
HTTP_PORT="${HTTP_PORT:-80}"
ENABLE_UFW="${ENABLE_UFW:-1}"
SERVER_IP="${SERVER_IP:-}"
MQTT_ALLOWED_IP="${MQTT_ALLOWED_IP:-}"
DB_NAME="${DB_NAME:-greenhouse}"
DB_USER="${DB_USER:-greenhouse}"
MQTT_USERNAME="${MQTT_USERNAME:-greenhouse}"
MQTT_PASSWORD="${MQTT_PASSWORD:-}"
INIT_SAMPLE_DATA="${INIT_SAMPLE_DATA:-false}"
ENABLE_MCP="${ENABLE_MCP:-auto}"
ENV_FILE="$PROJECT_DIR/.env"

GENERATED_DB_PASSWORD=0
GENERATED_ADMIN_PASSWORD=0
GENERATED_MQTT_PASSWORD=0

log()  { echo -e "\033[36m[deploy]\033[0m $*"; }
warn() { echo -e "\033[33m[deploy][warn]\033[0m $*"; }
die()  { echo -e "\033[31m[deploy][error]\033[0m $*" >&2; exit 1; }

[[ "${EUID}" -eq 0 ]] || die "请使用 root 或 sudo 运行本脚本"
[[ -f "$PROJECT_DIR/requirements.txt" ]] || die "未找到 $PROJECT_DIR/requirements.txt，请先把项目上传到 $PROJECT_DIR"
[[ -f "$PROJECT_DIR/app/main.py" ]] || die "目录结构不完整: 缺少 app/main.py"

# ============================================================
# 1. 系统依赖
# ============================================================
log "安装系统依赖..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    python3-venv python3-pip \
    mysql-server mosquitto mosquitto-clients \
    openssl curl ca-certificates ufw tar

# Nginx 单独安装：默认站点会尝试监听 80，若 80 已被 Docker 占用，
# 安装后的自动启动会失败，但包本身可用，随后我们会移除默认站点。
apt-get install -y -qq nginx || true
dpkg -s nginx >/dev/null 2>&1 || die "Nginx 安装失败"

# ============================================================
# 2. 2G 内存必备 swap
# ============================================================
if ! swapon --show 2>/dev/null | grep -q '/swapfile'; then
    log "创建 2G swap 文件..."
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo 'vm.swappiness=10' > /etc/sysctl.d/99-greenhouse-swap.conf
    sysctl -p /etc/sysctl.d/99-greenhouse-swap.conf >/dev/null
else
    log "swap 已存在，跳过"
fi

# ============================================================
# 3. 运行账号
# ============================================================
if ! id "$APP_USER" >/dev/null 2>&1; then
    log "创建系统账号 $APP_USER..."
    useradd -r -m -d "$PROJECT_DIR" -s /usr/sbin/nologin "$APP_USER"
fi
chown -R "$APP_USER:$APP_USER" "$PROJECT_DIR"

# ============================================================
# 4. 公网 IP
# ============================================================
if [[ -z "$SERVER_IP" ]]; then
    SERVER_IP="$(curl -s --max-time 5 https://api.ipify.org || true)"
fi
if [[ -z "$SERVER_IP" ]]; then
    SERVER_IP="$(hostname -I | awk '{print $1}')"
    warn "未能探测公网 IP，使用内网地址 $SERVER_IP 配置 CORS"
fi
log "服务器 IP: $SERVER_IP"

# ============================================================
# 5. MySQL 数据库与账号
# ============================================================
if [[ -z "${DB_PASSWORD:-}" ]]; then
    DB_PASSWORD="$(openssl rand -hex 16)"
    GENERATED_DB_PASSWORD=1
fi

log "创建数据库 $DB_NAME 与账号 $DB_USER..."
systemctl enable mysql >/dev/null 2>&1 || true
systemctl start mysql
if ! mysqladmin --protocol=socket -uroot ping >/dev/null 2>&1; then
    die "无法以 root 免密连接 MySQL。请先确认 mysql 服务已启动，或手动创建数据库与账号后重试"
fi
mysql --protocol=socket -uroot <<SQL
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'127.0.0.1' IDENTIFIED BY '$DB_PASSWORD';
ALTER USER '$DB_USER'@'127.0.0.1' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

if [[ ! -f /etc/mysql/mysql.conf.d/zz-greenhouse.cnf ]]; then
    log "写入 2G 内存 MySQL 调优配置..."
    cat > /etc/mysql/mysql.conf.d/zz-greenhouse.cnf <<'CNF'
[mysqld]
innodb_buffer_pool_size = 256M
max_connections = 50
performance_schema = OFF
CNF
    systemctl restart mysql
fi

# ============================================================
# 6. 生成 .env
# ============================================================
if [[ ! -f "$ENV_FILE" ]]; then
    log "未发现 .env，从 deploy/env.production.example 生成"
    cp "$SCRIPT_DIR/env.production.example" "$ENV_FILE"
fi

# 已有非默认 JWT 密钥则沿用，否则重新生成
if [[ -z "${JWT_SECRET:-}" ]]; then
    CURRENT_JWT="$(grep -E '^JWT_SECRET_KEY=' "$ENV_FILE" | head -n1 | cut -d= -f2- || true)"
    if [[ -z "$CURRENT_JWT" || "$CURRENT_JWT" == "CHANGE_ME" || "$CURRENT_JWT" == "6a9f2b3c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2" ]]; then
        JWT_SECRET="$(openssl rand -hex 32)"
    else
        JWT_SECRET="$CURRENT_JWT"
    fi
fi

# 已有非默认管理员密码则沿用，否则随机生成
if [[ -z "${ADMIN_PASSWORD:-}" ]]; then
    CURRENT_ADMIN="$(grep -E '^INIT_ADMIN_PASSWORD=' "$ENV_FILE" | head -n1 | cut -d= -f2- || true)"
    if [[ -z "$CURRENT_ADMIN" || "$CURRENT_ADMIN" == "CHANGE_ME" || "$CURRENT_ADMIN" == "Admin123456" ]]; then
        ADMIN_PASSWORD="$(openssl rand -hex 6)1a"
        GENERATED_ADMIN_PASSWORD=1
    else
        ADMIN_PASSWORD="$CURRENT_ADMIN"
    fi
fi

# MQTT 密码：优先环境变量，其次沿用 .env，最后随机生成
if [[ -z "$MQTT_PASSWORD" ]]; then
    CURRENT_MQTT_PASSWORD="$(grep -E '^MQTT_PASSWORD=' "$ENV_FILE" | head -n1 | cut -d= -f2- || true)"
    if [[ -z "$CURRENT_MQTT_PASSWORD" || "$CURRENT_MQTT_PASSWORD" == "CHANGE_ME" ]]; then
        MQTT_PASSWORD="$(openssl rand -hex 16)"
        GENERATED_MQTT_PASSWORD=1
    else
        MQTT_PASSWORD="$CURRENT_MQTT_PASSWORD"
    fi
fi

set_env() {
    local key="$1" value="$2"
    KEY="$key" VALUE="$value" FILE="$ENV_FILE" python3 - <<'PY'
import os

path = os.environ["FILE"]
key = os.environ["KEY"]
value = os.environ["VALUE"]

lines = []
if os.path.exists(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()

found = False
for i, line in enumerate(lines):
    if line.startswith(key + "="):
        lines[i] = f"{key}={value}"
        found = True
        break
if not found:
    lines.append(f"{key}={value}")

with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
PY
}

log "写入生产环境配置..."
set_env DATABASE_URL "mysql+pymysql://$DB_USER:$DB_PASSWORD@127.0.0.1:3306/$DB_NAME?charset=utf8mb4"
set_env JWT_SECRET_KEY "$JWT_SECRET"
set_env INIT_ADMIN_USERNAME "admin"
set_env INIT_ADMIN_PASSWORD "$ADMIN_PASSWORD"
set_env INIT_SAMPLE_DATA "$INIT_SAMPLE_DATA"
if [[ "$HTTP_PORT" == "80" ]]; then
    CORS_ORIGIN="http://$SERVER_IP"
else
    CORS_ORIGIN="http://$SERVER_IP:$HTTP_PORT"
fi
set_env CORS_ORIGINS "$CORS_ORIGIN"
set_env MQTT_BROKER_HOST "127.0.0.1"
set_env MQTT_BROKER_PORT "1883"
set_env MQTT_USERNAME "$MQTT_USERNAME"
set_env MQTT_PASSWORD "$MQTT_PASSWORD"
set_env AUTO_CREATE_DB "true"

chown "$APP_USER:$APP_USER" "$ENV_FILE"
chmod 600 "$ENV_FILE"

# ============================================================
# 7. Python 虚拟环境（跳过 torch/torchvision）
# ============================================================
if [[ ! -x "$PROJECT_DIR/.venv/bin/python" ]]; then
    log "创建 Python 虚拟环境..."
    sudo -u "$APP_USER" python3 -m venv "$PROJECT_DIR/.venv"
fi

log "安装 Python 依赖（跳过 PyTorch）..."
sudo -u "$APP_USER" "$PROJECT_DIR/.venv/bin/pip" install -q -U pip wheel
grep -vE '^(torch|torchvision)' "$PROJECT_DIR/requirements.txt" > /tmp/greenhouse-requirements.txt
sudo -u "$APP_USER" "$PROJECT_DIR/.venv/bin/pip" install -q -r /tmp/greenhouse-requirements.txt

# ============================================================
# 8. 初始化数据库
# ============================================================
log "初始化数据库表与种子数据..."
sudo -u "$APP_USER" bash -c "cd '$PROJECT_DIR' && .venv/bin/python -m app.scripts.init_db"

# ============================================================
# 9. systemd 服务
# ============================================================
log "安装 systemd 服务..."
install -m 644 "$SCRIPT_DIR/systemd/greenhouse-api.service" /etc/systemd/system/greenhouse-api.service
sed -i "s|__APP_DIR__|$PROJECT_DIR|g; s|__APP_USER__|$APP_USER|g" /etc/systemd/system/greenhouse-api.service

install -m 644 "$SCRIPT_DIR/systemd/greenhouse-mcp.service" /etc/systemd/system/greenhouse-mcp.service
sed -i "s|__APP_DIR__|$PROJECT_DIR|g; s|__APP_USER__|$APP_USER|g" /etc/systemd/system/greenhouse-mcp.service

# ============================================================
# 10. Nginx
# ============================================================
log "配置 Nginx..."
install -m 644 "$SCRIPT_DIR/nginx/greenhouse.conf" /etc/nginx/sites-available/greenhouse
sed -i "s|__WEB_ROOT__|$WEB_ROOT|g; s|__HTTP_PORT__|$HTTP_PORT|g" /etc/nginx/sites-available/greenhouse
ln -sfn /etc/nginx/sites-available/greenhouse /etc/nginx/sites-enabled/greenhouse
rm -f /etc/nginx/sites-enabled/default

mkdir -p "$WEB_ROOT"
if [[ -d "$PROJECT_DIR/frontend/dist" ]]; then
    log "部署前端构建产物到 $WEB_ROOT..."
    rm -rf "${WEB_ROOT:?}"/*
    cp -r "$PROJECT_DIR/frontend/dist/." "$WEB_ROOT/"
    chmod -R a+rX "$WEB_ROOT"
else
    warn "未找到 $PROJECT_DIR/frontend/dist，请先在本地 npm run build 并上传 dist"
fi

nginx -t
systemctl enable nginx >/dev/null 2>&1 || true
systemctl restart nginx || die "Nginx 启动失败，请检查端口 $HTTP_PORT 是否被占用"
systemctl is-active --quiet nginx || die "Nginx 未运行，请执行 journalctl -u nginx -n 50"

# ============================================================
# 11. Mosquitto
# ============================================================
log "配置 Mosquitto..."
command -v mosquitto_passwd >/dev/null 2>&1 || die "未找到 mosquitto_passwd，请确认 mosquitto 已安装"
if [[ -f /etc/mosquitto/passwd ]]; then
    mosquitto_passwd -b /etc/mosquitto/passwd "$MQTT_USERNAME" "$MQTT_PASSWORD"
else
    mosquitto_passwd -c -b /etc/mosquitto/passwd "$MQTT_USERNAME" "$MQTT_PASSWORD"
fi
chown mosquitto:mosquitto /etc/mosquitto/passwd
chmod 600 /etc/mosquitto/passwd
# 避免主配置里已有 listener 1883 导致端口冲突
if grep -qE '^[[:space:]]*listener[[:space:]]+1883' /etc/mosquitto/mosquitto.conf 2>/dev/null; then
    sed -i -E 's|^([[:space:]]*listener[[:space:]]+1883.*)$|# \1|' /etc/mosquitto/mosquitto.conf
fi
install -m 644 "$SCRIPT_DIR/mosquitto/greenhouse.conf" /etc/mosquitto/conf.d/greenhouse.conf
systemctl enable mosquitto >/dev/null 2>&1 || true
systemctl restart mosquitto || warn "Mosquitto 启动失败，请检查 /etc/mosquitto/conf.d/greenhouse.conf"

# ============================================================
# 12. 防火墙
# ============================================================
if [[ "$ENABLE_UFW" == "1" ]]; then
    log "配置 ufw..."
    ufw allow OpenSSH >/dev/null 2>&1 || true
    ufw allow "$HTTP_PORT/tcp" >/dev/null 2>&1 || true
    if [[ -n "$MQTT_ALLOWED_IP" ]]; then
        ufw allow from "$MQTT_ALLOWED_IP" to any port 1883 proto tcp >/dev/null 2>&1 || true
    else
        warn "未设置 MQTT_ALLOWED_IP，1883 未放行；请优先在阿里云安全组按来源 IP 放行"
    fi
    ufw --force enable >/dev/null 2>&1 || warn "ufw 启用失败，请手动检查"
else
    log "已跳过 ufw（ENABLE_UFW=0），请用阿里云安全组放行端口"
fi

# ============================================================
# 13. 启动服务
# ============================================================
log "启动后端服务..."
systemctl daemon-reload
systemctl enable greenhouse-api >/dev/null 2>&1 || true
systemctl restart greenhouse-api

MCP_ENDPOINT_VALUE="$(grep -E '^MCP_ENDPOINT=' "$ENV_FILE" | head -n1 | cut -d= -f2- || true)"
if [[ "$ENABLE_MCP" == "1" || ( "$ENABLE_MCP" == "auto" && -n "$MCP_ENDPOINT_VALUE" ) ]]; then
    log "启动 MCP 桥接服务..."
    systemctl enable greenhouse-mcp >/dev/null 2>&1 || true
    systemctl restart greenhouse-mcp || warn "MCP 桥接启动失败，查看 journalctl -u greenhouse-mcp"
else
    systemctl disable greenhouse-mcp >/dev/null 2>&1 || true
    log "未启用 MCP 桥接（可用 ENABLE_MCP=1 开启）"
fi

# 健康检查
HEALTH_OK=0
for _ in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:8001/health >/dev/null 2>&1; then
        HEALTH_OK=1
        break
    fi
    sleep 1
done

echo
echo "============================================================"
echo " 部署完成"
echo "============================================================"
if [[ "$HEALTH_OK" -eq 1 ]]; then
    echo " 后端健康检查: OK"
else
    echo " 后端健康检查: 失败，请执行 journalctl -u greenhouse-api -n 100"
fi
if [[ "$HTTP_PORT" == "80" ]]; then
    ACCESS_URL="http://$SERVER_IP"
else
    ACCESS_URL="http://$SERVER_IP:$HTTP_PORT"
fi
echo " 访问地址:     $ACCESS_URL"
echo " 管理员账号:   admin"
if [[ "$GENERATED_ADMIN_PASSWORD" -eq 1 ]]; then
    echo " 管理员密码:   $ADMIN_PASSWORD   （随机生成，请立即保存）"
else
    echo " 管理员密码:   沿用 .env 中的现有值"
fi
if [[ "$GENERATED_DB_PASSWORD" -eq 1 ]]; then
    echo " 数据库密码:   $DB_PASSWORD     （已写入 .env，请妥善保存）"
fi
echo " MQTT 账号:    $MQTT_USERNAME"
echo " MQTT 密码:    $MQTT_PASSWORD"
echo "               ↑ 请填入上位机 wifi_config.h 的 MQTT_USERNAME / MQTT_PASSWORD 并重新烧录"
echo
echo " 常用命令:"
echo "   systemctl status greenhouse-api"
echo "   journalctl -u greenhouse-api -f"
echo "   nginx -t && systemctl reload nginx"
echo "   mosquitto_sub -h 127.0.0.1 -t greenhouse/sensor/data -v"
echo "============================================================"
