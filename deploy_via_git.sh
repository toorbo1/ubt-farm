#!/bin/bash
# Деплой через Git на сервер
# Использование: ./deploy_via_git.sh

SERVER="root@144.31.25.159"
REMOTE_DIR="/opt/ubt-farm"
REPO_URL="https://github.com/toorbo1/ubt-farm.git"

echo "========================================="
echo "  Деплой UBT Farm через Git"
echo "========================================="

# Подключение к серверу и деплой
ssh $SERVER << EOF
set -e

echo "[1/6] Проверка директории..."
if [ ! -d "$REMOTE_DIR/.git" ]; then
    echo "  > Создаем директорию и клонируем репо..."
    mkdir -p $REMOTE_DIR
    cd /opt
    git clone $REPO_URL ubt-farm
else
    echo "  > Директория с git уже существует"
fi

cd $REMOTE_DIR

echo "[2/6] Pull последних изменений..."
git pull origin main

echo "[3/6] Установка зависимостей..."
python3 -m venv venv
venv/bin/pip install -q -U pip setuptools wheel
venv/bin/pip install -q -r requirements.txt

echo "[4/6] Установка Playwright..."
venv/bin/python3 -m playwright install chromium --with-deps > /dev/null 2>&1

echo "[5/6] Настройка PM2..."
pm2 delete ubt-bot1 ubt-bot2 2>/dev/null || true
pm2 start ecosystem.config.js
pm2 save

echo "[6/6] Проверка статуса..."
pm2 status | grep ubt

echo ""
echo "========================================="
echo "  Деплой завершен!"
echo "========================================="
echo "Логи бота: pm2 logs ubt-bot1 --lines 20"
echo "Редактировать .env: nano $REMOTE_DIR/.env"
EOF

echo "Готово!"
