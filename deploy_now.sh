#!/bin/bash
# ============================================================
# deploy_now.sh — Скрипт для выполнения НА СЕРВЕРЕ
# Запускать после подключения по SSH: bash deploy_now.sh
# ============================================================

set -e

APP_DIR="/opt/ubt-farm"
cd "$APP_DIR" || { echo "Ошибка: директория $APP_DIR не найдена"; exit 1; }

echo ""
echo "========================================="
echo "  Деплой обновлений UBT Farm"
echo "========================================="
echo ""

# 1. Бэкап
echo "[1/5] Создаю бэкап..."
BACKUP_DIR="$APP_DIR/backups/deploy_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp config/settings.py core/subtitle_timing.py video_engine/builder.py \
   core/llm_client.py core/image_gen.py core/video_ai.py bot/handlers.py \
   "$BACKUP_DIR/" 2>/dev/null || true
echo "      Бэкап: $BACKUP_DIR"

# 2. Проверка файлов (они должны быть уже загружены)
echo "[2/5] Проверяю файлы..."
for f in config/settings.py core/subtitle_timing.py video_engine/builder.py \
         core/llm_client.py core/image_gen.py core/video_ai.py bot/handlers.py; do
    if [ -f "$f" ]; then
        echo "      ✓ $f"
    else
        echo "      ✗ $f НЕ НАЙДЕН!"
    fi
done

# 3. Очистка кэша
echo "[3/5] Очищаю Python-кэш..."
rm -rf bot/__pycache__ config/__pycache__ core/__pycache__ \
       video_engine/__pycache__ uploader/__pycache__ uniqueizer/__pycache__

# 4. Проверка синтаксиса
echo "[4/5] Проверяю синтаксис..."
if ./venv/bin/python3 -m py_compile config/settings.py core/subtitle_timing.py \
    video_engine/builder.py core/llm_client.py core/image_gen.py core/video_ai.py \
    bot/handlers.py 2>&1; then
    echo "      ✓ Синтаксис OK"
else
    echo "      ✗ Ошибка компиляции! Откатываю бэкап..."
    cp "$BACKUP_DIR"/*.py . 2>/dev/null || true
    exit 1
fi

# 5. Перезапуск ботов
echo "[5/5] Перезапускаю ботов..."
pm2 restart ubt-bot1 ubt-bot2 2>/dev/null || pm2 restart ubt-bot1 2>/dev/null || true

sleep 3
echo ""
echo "Статус ботов:"
pm2 status | grep ubt-bot || echo "Боты не запущены"

echo ""
echo "========================================="
echo "  Деплой завершён!"
echo "========================================="
echo ""
echo "Проверьте логи: pm2 logs ubt-bot1 --lines 30"
echo "Откат при необходимости: cp $BACKUP_DIR/*.py ."
echo ""
