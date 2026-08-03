#!/bin/bash
# ============================================================
# deploy.sh — Деплой UBT Traffic Farm + VPN Monitor Bot
# ============================================================
# Запуск: chmod +x deploy.sh && bash deploy.sh
#
# Что делает:
#   1. Устанавливает Python 3, pip, ffmpeg, git
#   2. Создаёт пользователя ubtbot
#   3. Клонирует/обновляет проект
#   4. Устанавливает Python-зависимости
#   5. Устанавливает Playwright (Chromium)
#   6. Настраивает PM2 для автозапуска бота
#   7. Настраивает logrotate
# ============================================================

set -e

APP_DIR="/opt/ubt-farm"
REPO_URL=""  # укажите ваш git-репозиторий или скопируйте файлы вручную
BOT_USER="ubtbot"
BOT_TOKEN_1="${TELEGRAM_BOT_TOKEN:-8427880718:AAFIE85dNPEVW5HFIXmj7uvviK5ZExqV-mw}"
BOT_TOKEN_2="${TELEGRAM_BOT_TOKEN_2:-8760700962:AAFHtirhjGkDQMN7nC5VthqB0e3DU2Zatjo}"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; }

# --- Проверка прав ---
if [[ $EUID -ne 0 ]]; then
   err "Запусти с sudo: sudo bash deploy.sh"
   exit 1
fi

echo ""
echo "==========================================="
echo "  UBT Traffic Farm + VPN Monitor — Деплой"
echo "==========================================="
echo ""

# 1. Системные пакеты
log "Устанавливаю системные пакеты..."
apt-get update -qq
apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    ffmpeg \
    git \
    curl \
    wget \
    ca-certificates \
    gnupg \
    > /dev/null 2>&1
log "Системные пакеты установлены"

# 2. Node.js + PM2 (если ещё нет)
if ! command -v node &>/dev/null; then
    log "Устанавливаю Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs > /dev/null 2>&1
fi

if ! command -v pm2 &>/dev/null; then
    log "Устанавливаю PM2..."
    npm install -g pm2 > /dev/null 2>&1
    pm2 install pm2-logrotate > /dev/null 2>&1
fi
log "Node.js $(node -v) + PM2 готовы"

# 3. Пользователь
if ! id -u "$BOT_USER" &>/dev/null; then
    log "Создаю пользователя $BOT_USER..."
    useradd -m -s /bin/bash "$BOT_USER"
fi

# 4. Директория проекта
log "Настраиваю $APP_DIR..."
mkdir -p "$APP_DIR"
mkdir -p "$APP_DIR/logs"
mkdir -p "$APP_DIR/assets/backgrounds"
mkdir -p "$APP_DIR/assets/fonts"
mkdir -p "$APP_DIR/output"
mkdir -p "$APP_DIR/profiles"

# Копируем файлы проекта (если скрипт лежит рядом с проектом)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ "$SCRIPT_DIR" != "$APP_DIR" ]]; then
    log "Копирую файлы проекта из $SCRIPT_DIR..."
    rsync -a --exclude='.git' --exclude='__pycache__' \
          --exclude='*.pyc' --exclude='node_modules' \
          --exclude='.env' \
          "$SCRIPT_DIR/" "$APP_DIR/"
fi

cd "$APP_DIR"

# 5. Виртуальное окружение
if [[ ! -d "venv" ]]; then
    log "Создаю виртуальное окружение..."
    python3 -m venv venv
fi
source venv/bin/activate

log "Устанавливаю Python-зависимости..."
pip install --quiet -U pip setuptools wheel > /dev/null 2>&1
pip install --quiet -r requirements.txt > /dev/null 2>&1

# 6. Playwright (Chromium)
log "Устанавливаю Playwright браузеры..."
python3 -m playwright install chromium > /dev/null 2>&1
python3 -m playwright install-deps chromium > /dev/null 2>&1

# 7. .env
if [[ ! -f ".env" ]]; then
    log "Создаю .env из шаблона..."
    cp .env.example .env
fi

# Обновляем токены в .env (если переданы через переменные окружения)
sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$BOT_TOKEN_1|" .env 2>/dev/null || true
sed -i "s|^TELEGRAM_BOT_TOKEN_2=.*|TELEGRAM_BOT_TOKEN_2=$BOT_TOKEN_2|" .env 2>/dev/null || true

chown -R "$BOT_USER:$BOT_USER" "$APP_DIR"
chmod 750 "$APP_DIR/.env"

# 8. PM2 ecosystem
log "Настраиваю PM2 ecosystem..."
cat > ecosystem.config.js << 'PM2EOF'
module.exports = {
  apps: [
    {
      name: "ubt-bot1",
      script: "bot/run_bot.py",
      interpreter: "venv/bin/python3",
      args: "--bot 1",
      cwd: "APP_DIR_PLACEHOLDER",
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
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
      cwd: "APP_DIR_PLACEHOLDER",
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
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

sed -i "s|APP_DIR_PLACEHOLDER|$APP_DIR|g" ecosystem.config.js

# 9. Logrotate
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

# 10. Запуск
log "Запускаю ботов через PM2..."
su -c "cd $APP_DIR && $APP_DIR/venv/bin/pm2 start ecosystem.config.js" -s /bin/bash "$BOT_USER" 2>/dev/null || \
    sudo -u "$BOT_USER" bash -c "cd $APP_DIR && $APP_DIR/venv/bin/pm2 start ecosystem.config.js"

# 11. PM2 автозапуск
log "Настраиваю автозапуск PM2..."
env PATH=\$PATH:$APP_DIR/venv/bin pm2 startup systemd -u "$BOT_USER" --hp "/home/$BOT_USER" 2>/dev/null || true
su -c "pm2 save" -s /bin/bash "$BOT_USER" 2>/dev/null || true

echo ""
log "==========================================="
log "  Деплой завершён!"
log "==========================================="
echo ""
echo "  Боты запущены:"
echo "    • Bot 1 (основной):  pm2 show ubt-bot1"
echo "    • Bot 2 (новый):     pm2 show ubt-bot2"
echo ""
echo "  Логи:"
echo "    • Bot 1:  tail -f $APP_DIR/logs/bot1-out.log"
echo "    • Bot 2:  tail -f $APP_DIR/logs/bot2-out.log"
echo ""
echo "  Управление:"
echo "    pm2 stop ubt-bot1"
echo "    pm2 restart ubt-bot1"
echo "    pm2 logs ubt-bot1 --lines 50"
echo ""
echo "  Настройки: $APP_DIR/.env"
echo "  Видео:     $APP_DIR/output/"
echo "  Фоны:      $APP_DIR/assets/backgrounds/"
echo ""
