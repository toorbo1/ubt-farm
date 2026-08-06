#!/bin/bash
# ============================================================
# deploy_to_server.sh — Полный деплой с локальной машины
# Запуск: bash deploy_to_server.sh
# ============================================================

set -e

SERVER_USER="root"
SERVER_HOST="144.31.25.159"
APP_DIR="/opt/ubt-farm"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; }

echo ""
echo "==========================================="
echo "  Деплой UBT Farm на сервер"
echo "==========================================="
echo ""

# Проверяем подключение к серверу
echo "[1/4] Проверяю подключение..."
if ssh -o StrictHostKeyChecking=no -o BatchMode=yes ${SERVER_USER}@${SERVER_HOST} "echo connected" &>/dev/null; then
    log "Подключение успешно"
else
    err "Не удалось подключиться к серверу"
    echo "Проверьте SSH ключи и доступность сервера"
    exit 1
fi

# Создаём временную директорию для загрузки
TEMP_DIR=$(mktemp -d)
log "Создана временная директория: $TEMP_DIR"

# Копируем изменённые файлы во временную директорию
echo "[2/4] Подготавливаю файлы..."
mkdir -p "$TEMP_DIR/bot"
cp bot/handlers.py "$TEMP_DIR/bot/"
cp bot/keyboards.py "$TEMP_DIR/bot/"
cp bot/run_bot.py "$TEMP_DIR/bot/"
log "Файлы скопированы"

# Загружаем файлы на сервер
echo "[3/4] Загружаю файлы на сервер..."
scp -o StrictHostKeyChecking=no \
    "$TEMP_DIR/bot/handlers.py" \
    "$TEMP_DIR/bot/keyboards.py" \
    "$TEMP_DIR/bot/run_bot.py" \
    ${SERVER_USER}@${SERVER_HOST}:${APP_DIR}/bot/
log "Файлы загружены"

# Очищаем временную директорию
rm -rf "$TEMP_DIR"

# Выполняем деплой на сервере
echo "[4/4] Запускаю деплой на сервере..."
ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_HOST} << 'EOF'
cd /opt/ubt-farm

# Бэкап
BACKUP_DIR="/opt/ubt-farm/backups/deploy_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp bot/*.py "$BACKUP_DIR/" 2>/dev/null || true
echo "Бэкап создан: $BACKUP_DIR"

# Очистка кэша
rm -rf bot/__pycache__

# Проверка синтаксиса
if venv/bin/python3 -m py_compile bot/handlers.py bot/keyboards.py bot/run_bot.py 2>&1; then
    echo "Синтаксис OK"
else
    echo "Ошибка компиляции! Откат..."
    cp "$BACKUP_DIR"/*.py bot/ 2>/dev/null || true
    exit 1
fi

# Перезапуск ботов
pm2 restart ubt-bot1 ubt-bot2 || pm2 restart all
sleep 3

echo ""
echo "Статус:"
pm2 status | grep ubt-bot || echo "Боты не запущены"
echo ""
echo "Деплой завершён!"
EOF

echo ""
log "==========================================="
log "  Деплой завершён!"
log "==========================================="
echo ""
echo "Проверьте логи: ssh root@144.31.25.159 'pm2 logs ubt-bot1 --lines 30'"
