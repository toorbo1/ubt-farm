#!/bin/bash
# ============================================================
# СКОПИРУЙ ЭТОТ ФАЙЛ НА ТЕЛЕФОН И ВЫПОЛНИ В TERMUX:
# bash INSTALL_ON_PHONE.sh
# ============================================================

echo "🚀 Установка UBT Farm на Termux..."

# Обновление системы
echo "[1/6] Обновление пакетов..."
pkg update -y && pkg upgrade -y

# Установка зависимостей
echo "[2/6] Установка Python, FFmpeg..."
pkg install -y python git ffmpeg openssh wget curl

# Создание директории
echo "[3/6] Создание папки проекта..."
mkdir -p ~/ubt-farm
cd ~/ubt-farm

# Настройка Python окружения
echo "[4/6] Создание виртуального окружения..."
python -m venv venv
source venv/bin/activate

# Установка библиотек
echo "[5/6] Установка Flask и зависимостей..."
pip install flask boto3 pydantic-settings httpx pillow

# Проверка наличия файлов проекта
if [ ! -f "web_app/app.py" ]; then
    echo "[ОШИБКА] Файлы проекта не найдены!"
    echo "Скопируй папку web_app из ПК в ~/ubt-farm/"
    echo "Можно через adb:"
    echo "  adb push C:/Users/User/Desktop/убт/web_app /sdcard/ubt-farm/"
    echo "Или скачай с GitHub:"
    echo "  git clone <your-repo-url>"
    exit 1
fi

echo "[6/6] ГОТОВО!"
echo ""
echo "Для запуска сервера выполни:"
echo "  cd ~/ubt-farm"
echo "  source venv/bin/activate"
echo "  python web_app/app.py --port 5001"
echo ""
echo "После этого открой на телефоне:"
echo "  http://localhost:5001"
echo ""
echo "API ключ уже настроен: sk-smart-_0uezNrlxMhc4zZGmjZQpdAZl8adsHe2KpFgaFzcIKs"
