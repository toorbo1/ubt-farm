#!/bin/bash
# ============================================================
# deploy_on_server.sh — ЗАПУСКАТЬ НА СЕРВЕРЕ 144.31.25.159
# ============================================================
# Как использовать:
#   Вариант A: залить на сервер и запустить
#     scp deploy_on_server.sh root@144.31.25.159:/root/
#     ssh root@144.31.25.159 "bash /root/deploy_on_server.sh"
#
#   Вариант B: скопировать текст и вставить в консоль сервера
# ============================================================

set -e

APP_DIR="/opt/ubt-farm"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

# Убедимся что мы на сервере
if [[ "$(hostname -I 2>/dev/null | awk '{print $1}')" != "144.31.25.159" ]]; then
    warn "Этот скрипт должен запускаться на сервере 144.31.25.159"
    echo "Продолжить? (y/n): "; read confirm
    [[ "$confirm" != "y" ]] && exit 1
fi

echo ""
echo "==========================================="
echo "  Установка UBT Farm на сервер"
echo "==========================================="
echo ""

# 1. Системные пакеты
log "Устанавливаю системные пакеты..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv ffmpeg git curl > /dev/null 2>&1

# 2. Node.js + PM2
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs > /dev/null 2>&1
fi
if ! command -v pm2 &>/dev/null; then
    npm install -g pm2 > /dev/null 2>&1
fi
log "Node.js $(node -v) + PM2"

# 3. Директория проекта
log "Создаю $APP_DIR..."
mkdir -p "$APP_DIR"/{bot,config,core,video_engine,uploader,uniqueizer,storage}
mkdir -p "$APP_DIR"/assets/{backgrounds,fonts}
mkdir -p "$APP_DIR"/{output,logs,profiles}

# 4. Проверяем, есть ли уже файлы
if [[ -z "$(ls -A "$APP_DIR/bot/" 2>/dev/null)" ]]; then
    log "Копирую файлы из текущей директории..."
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    rsync -a --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='venv' --exclude='node_modules' "$SCRIPT_DIR/" "$APP_DIR/" 2>/dev/null || {
        warn "Файлы не найдены рядом. Создаю пустой проект."
        echo "Скопируй файлы в $APP_DIR вручную через SCP."
    }
fi

cd "$APP_DIR"

# 5. Устанавливаем файлы проекта (если их нет — создаём базовую структуру)
if [[ ! -f "$APP_DIR/requirements.txt" ]]; then
    log "Загружаю файлы проекта из репозитория..."
    # Если есть git — клонируем
    # git clone https://github.com/... .
    # Пока просто создаём заглушку
    warn "Файлы проекта не найдены. Используй SCP:"
    echo "  scp -r /path/to/ubt/* root@144.31.25.159:$APP_DIR/"
    echo ""
    echo "Или загрузи руками, затем запусти скрипт снова."
    exit 1
fi

# 6. Виртуальное окружение
log "Настраиваю Python..."
python3 -m venv venv
source venv/bin/activate
pip install -q -U pip setuptools wheel > /dev/null 2>&1
pip install -q -r requirements.txt > /dev/null 2>&1
log "Python зависимости установлены"

# 7. Playwright
log "Устанавливаю Playwright..."
python3 -m playwright install chromium > /dev/null 2>&1
python3 -m playwright install-deps chromium > /dev/null 2>&1
log "Playwright + Chromium готовы"

# 8. .env
if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
        cp .env.example .env
        warn "Создан .env из примера — отредактируй токены!"
    fi
fi

# 9. PM2 ecosystem
log "Настраиваю PM2..."
cat > ecosystem.config.js << 'PM2EOF'
module.exports = {
  apps: [
    {
      name: "ubt-bot1",
      script: "bot/run_bot.py",
      interpreter: "venv/bin/python3",
      args: "--bot 1",
      cwd: "/opt/ubt-farm",
      error_file: "./logs/bot1-error.log",
      out_file: "./logs/bot1-out.log",
      merge_logs: true,
      max_memory_restart: "500M",
      max_restarts: 10,
      restart_delay: 5000,
    },
    {
      name: "ubt-bot2",
      script: "bot/run_bot.py",
      interpreter: "venv/bin/python3",
      args: "--bot 2",
      cwd: "/opt/ubt-farm",
      error_file: "./logs/bot2-error.log",
      out_file: "./logs/bot2-out.log",
      merge_logs: true,
      max_memory_restart: "500M",
      max_restarts: 10,
      restart_delay: 5000,
    },
  ],
};
PM2EOF

# 10. Logrotate
log "Настраиваю logrotate..."
cat > /etc/logrotate.d/ubt-farm << 'LOGEOF'
/opt/ubt-farm/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
LOGEOF

# 11. Запуск
log "Запускаю ботов..."
pm2 delete ubt-bot1 ubt-bot2 2>/dev/null || true
pm2 start ecosystem.config.js
pm2 save
pm2 startup 2>/dev/null || true

echo ""
log "==========================================="
log "  Деплой завершён!"
log "==========================================="
echo ""
echo "  Статус:  pm2 status"
echo "  Bot 1:   pm2 logs ubt-bot1 --lines 20"
echo "  Bot 2:   pm2 logs ubt-bot2 --lines 20"
echo "  .env:    nano $APP_DIR/.env"
echo "  Видео:   ls -la $APP_DIR/output/"
echo ""
