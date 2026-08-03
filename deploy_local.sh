#!/bin/bash
# ============================================================
# deploy_local.sh — Быстрый деплой на локальную Ubuntu-машину
# ============================================================
# Просто запусти: sudo bash deploy_local.sh
# Всё настроит автоматом в /opt/ubt-farm

set -e

APP_DIR="/opt/ubt-farm"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Цвета
GREEN='\033[0;32m'
NC='\033[0m'
log() { echo -e "${GREEN}[✓]${NC} $1"; }

if [[ $EUID -ne 0 ]]; then
   echo "Запусти с sudo: sudo bash deploy_local.sh"
   exit 1
fi

# Системные пакеты
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv ffmpeg > /dev/null 2>&1
log "Системные пакеты"

# Node.js + PM2
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs > /dev/null 2>&1
fi
npm install -g pm2 > /dev/null 2>&1
log "Node.js + PM2"

# Директория
mkdir -p "$APP_DIR"/{logs,assets/{backgrounds,fonts},output,profiles,bot,config,core,video_engine,uploader,uniqueizer,storage}

# Копируем всё (кроме .git, __pycache__)
rsync -a --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='node_modules' "$SCRIPT_DIR/" "$APP_DIR/"
log "Файлы проекта"

# Виртуальное окружение
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install -q -U pip setuptools wheel > /dev/null 2>&1
pip install -q -r requirements.txt > /dev/null 2>&1
python3 -m playwright install chromium > /dev/null 2>&1
python3 -m playwright install-deps chromium > /dev/null 2>&1
log "Python + Playwright"

# .env
if [[ ! -f .env ]]; then
    cp .env.example .env
    log "Создан .env — отредактируй токены!"
fi

# PM2 ecosystem
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [
    { name: "ubt-bot1", script: "bot/run_bot.py", interpreter: "venv/bin/python3",
      args: "--bot 1", cwd: "$APP_DIR",
      error_file: "./logs/bot1-error.log", out_file: "./logs/bot1-out.log",
      merge_logs: true, max_memory_restart: "500M", max_restarts: 10, restart_delay: 5000 },
    { name: "ubt-bot2", script: "bot/run_bot.py", interpreter: "venv/bin/python3",
      args: "--bot 2", cwd: "$APP_DIR",
      error_file: "./logs/bot2-error.log", out_file: "./logs/bot2-out.log",
      merge_logs: true, max_memory_restart: "500M", max_restarts: 10, restart_delay: 5000 },
  ],
};
EOF

pm2 start ecosystem.config.js
pm2 save
pm2 startup systemd -u root --hp /root 2>/dev/null || true
log "PM2 запущен"

echo ""
echo "============================================"
echo "  Деплой завершён!"
echo "  Bot 1: pm2 logs ubt-bot1"
echo "  Bot 2: pm2 logs ubt-bot2"
echo "  .env:  $APP_DIR/.env"
echo "============================================"
