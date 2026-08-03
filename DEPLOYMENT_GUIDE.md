# UBT Traffic Farm - Полная документация

## 🚀 Быстрый старт

### Вариант 1: Бесплатный хостинг (Render.com)

**Шаги:**
1. Регистрация на https://render.com (бесплатно, без карты)
2. Создать Web Service
3. Подключить GitHub репозиторий или загрузить файлы
4. Настроить переменные окружения (.env)
5. Деплой автоматический

**Лимиты бесплатного тарифа:**
- 750 часов/месяц (достаточно для 1 бота)
- 512 MB RAM
- После 15 мин неактивности — засыпает (первый запрос медленный)

### Вариант 2: Koyeb.com (лучше Render)

- Бесплатно навсегда
- Не засыпает
- 2 GB RAM
- Python + FFmpeg поддерживается

**Инструкция по деплою на Koyeb:**

```bash
# 1. Создать аккаунт на koyeb.com
# 2. Нажать "Create Service"
# 3. Выбрать "Deploy from Git" или "Deploy from Docker"
# 4. Добавить переменные окружения из .env
# 5. Deploy!
```

### Вариант 3: Oracle Cloud Always Free

- 4 ARM CPU + 24 GB RAM (!)
- Полностью бесплатно навсегда
- Нужна карта для регистрации (но не списывает)
- Ubuntu Linux VPS

---

## 📱 Termux на телефоне

### Установка:

1. Установить Termux из F-Droid (НЕ из Google Play!)
   - Скачать: https://f-droid.org/packages/com.termux/

2. Настройка:
```bash
# Обновить пакеты
pkg update && pkg upgrade

# Установить Python и зависимости
pkg install python git ffmpeg openssh

# Клонировать проект
git clone <your-repo-url>
cd ubt

# Создать venv
python -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Запустить бота
python bot/run_bot.py --bot 1
```

3. Подключение к ПК через ADB:
```bash
# На ПК (Windows):
adb tcpip 5555
adb connect <IP_телефона>:5555

# Теперь можно запускать команды с телефона
```

---

## 🔧 Переменные окружения (.env)

```env
# Bot tokens
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_BOT_TOKEN_2=second_bot_token

# LLM (OpenRouter) - НЕ ИСПОЛЬЗУЕТСЯ, используем фолбэк
LLM_API_KEY=sk-smart-_0uezNrlxMhc4zZGmjZQpdAZl8adsHe2KpFgaFzcIKs

# Image Generation
REPLICATE_API_KEY=r8_your_key_here  # Получить на replicate.com

# Video
USE_AI_VIDEO=true
FAL_API_KEY=fe1f6926-b892-4b68-b2cd-5e92d1822ea7:2673aa1399b34ed7462ada50eacf6dfc

# Gemini (для картинок)
GEMINI_API_KEYS=key1,key2
```

---

## 🎨 Качество генерации

### Картинки:
- **Pollinations.ai** — бесплатно, без ключа
- Промпты автоматически улучшаются
- Размер: 576x1024 → upscale до 1080x1920 с AI-enhancement

### Видео:
- **Ken Burns** анимация (локально)
- **fal.ai** — если есть баланс
- Разные движения камеры (zoom, pan, rotate)

### Сценарии:
- Комбинаторные промпты (6 пулов × 6-12 вариантов)
- Гарантированная уникальность каждой сцены

---

## 🐛 Troubleshooting

### Проблема: Картинки сплющенные
**Решение:** `_finalize_image()` в `core/image_gen.py` делает crop к 9:16

### Проблема: Сценарий не генерируется
**Решение:** Используем фолбэк-промпты, API не нужен

### Проблема: Бот падает на сервере
**Решение:** Проверить логи PM2: `pm2 logs ubt-bot1`

---

## 📊 Мониторинг

```bash
# Статус ботов
pm2 status

# Логи
pm2 logs ubt-bot1 --lines 50

# Ресурсы
pm2 monit
```

---

## 🔄 Авто-деплой при коммите

Создать `.github/workflows/deploy.yml`:

```yaml
name: Auto Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Koyeb
        uses: koyeb-io/koyeb-action@v1
        with:
          service: ubt-bot
          token: ${{ secrets.KOYEB_API_TOKEN }}
```

---

## 📞 Контакты поддержки

- Telegram: @ubt_support
- Email: support@ubt-farm.local
