#!/bin/bash
# ============================================================
# deploy_remote.sh — Деплой UBT Farm на 144.31.25.159
# ============================================================
# Использование:
#   chmod +x deploy_remote.sh
#   ./deploy_remote.sh                    # спросит пароль
#   ./deploy_remote.sh --key ~/.ssh/id_rsa  # по SSH-ключу
#
# Что делает:
#   1. Копирует все файлы проекта на сервер
#   2. Устанавливает зависимости
#   3. Настраивает PM2 для автозапуска
#   4. Запускает обоих ботов
# ============================================================

set -e

REMOTE_HOST="144.31.25.159"
REMOTE_PORT="22"
REMOTE_USER="root"
REMOTE_DIR="/opt/ubt-farm"
SSH_KEY=""

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

# Парсинг аргументов
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --key) SSH_KEY="$2"; shift ;;
        --host) REMOTE_HOST="$2"; shift ;;
        --user) REMOTE_USER="$2"; shift ;;
        *) err "Неизвестный параметр: $1"; exit 1 ;;
    esac
    shift
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "==========================================="
echo "  Деплой UBT Farm → $REMOTE_HOST"
echo "==========================================="
echo ""

# SSH опции
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
if [[ -n "$SSH_KEY" ]]; then
    SSH_OPTS="$SSH_OPTS -i $SSH_KEY"
fi

# 1. Проверка подключения
log "Проверяю подключение к $REMOTE_HOST..."
ssh $SSH_OPTS "${REMOTE_USER}@${REMOTE_HOST}" "echo OK" || {
    err "Не могу подключиться к $REMOTE_HOST"
    exit 1
}

# 2. Создаём директории на сервере
log "Создаю директории..."
ssh $SSH_OPTS "${REMOTE_USER}@${REMOTE_HOST}" "
    mkdir -p $REMOTE_DIR/{bot,config,core,video_engine,uploader,uniqueizer,storage}
    mkdir -p $REMOTE_DIR/assets/{backgrounds,fonts,cta_templates}
    mkdir -p $REMOTE_DIR/output
    mkdir -p $REMOTE_DIR/logs
    mkdir -p $REMOTE_DIR/profiles
"

# 3. Копируем файлы (rsync)
log "Копирую файлы проекта..."
rsync -avz --progress \
    -e "ssh $SSH_OPTS" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='venv' \
    --exclude='node_modules' \
    --exclude='.env' \
    --exclude='output/*.mp4' \
    "$SCRIPT_DIR/" \
    "${REMOTE_USER}@${REMOTE_HOST}:$REMOTE_DIR/"

# 4. Запускаем установку на сервере
log "Устанавливаю зависимости на сервере..."
ssh $SSH_OPTS "${REMOTE_USER}@${REMOTE_HOST}" "
set -e
cd $REMOTE_DIR

# Системные пакеты
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv ffmpeg > /dev/null 2>&1

# Node.js + PM2
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs > /dev/null 2>&1
fi
npm install -g pm2 > /dev/null 2>&1
echo '  [✓] Node.js + PM2'

# Python venv
if [[ ! -d venv ]]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -U pip setuptools wheel > /dev/null 2>&1
pip install -q -r requirements.txt > /dev/null 2>&1
echo '  [✓] Python зависимости'

# Playwright
python3 -m playwright install chromium > /dev/null 2>&1
python3 -m playwright install-deps chromium > /dev/null 2>&1
echo '  [✓] Playwright + Chromium'

# .env (если нет — копируем из примера)
if [[ ! -f .env ]]; then
    cp .env.example .env
    echo '  [!] Создан .env — заполни токены!'
fi

# PM2 ecosystem
cat > ecosystem.config.js << 'PM2EOF'
module.exports = {
  apps: [
    { name: 'ubt-bot1', script: 'bot/run_bot.py', interpreter: 'venv/bin/python3',
      args: '--bot 1', cwd: '$REMOTE_DIR',
      error_file: './logs/bot1-error.log', out_file: './logs/bot1-out.log',
      merge_logs: true, max_memory_restart: '500M', max_restarts: 10, restart_delay: 5000 },
    { name: 'ubt-bot2', script: 'bot/run_bot.py', interpreter: 'venv/bin/python3',
      args: '--bot 2', cwd: '$REMOTE_DIR',
      error_file: './logs/bot2-error.log', out_file: './logs/bot2-out.log',
      merge_logs: true, max_memory_restart: '500M', max_restarts: 10, restart_delay: 5000 },
  ],
};
PM2EOF

# Запуск
pm2 delete ubt-bot1 ubt-bot2 2>/dev/null || true
pm2 start ecosystem.config.js
pm2 save
pm2 startup systemd -u root --hp /root 2>/dev/null || true

# Logrotate
cat > /etc/logrotate.d/ubt-farm << 'LOGEOF'
$REMOTE_DIR/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
LOGEOF

echo ''
echo '==========================================='
echo '  Деплой завершён!'
echo '==========================================='
echo ''
echo '  Bot 1: pm2 status ubt-bot1'
echo '  Bot 2: pm2 status ubt-bot2'
echo '  Логи:  pm2 logs ubt-bot1'
echo '  .env:  $REMOTE_DIR/.env'
echo ''
"

log "Готово! Бот запущен на $REMOTE_HOST"
