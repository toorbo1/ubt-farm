# Инструкция по деплою на сервер 144.31.25.159

## Файлы для обновления (только эти 7 файлов):

```
config/settings.py          — настройки субтитров (шрифт, отступы)
core/subtitle_timing.py     — генерация ASS-субтитров
video_engine/builder.py     — сборка видео + ассемблирование
core/llm_client.py          — фолбэк-промпты сцен
core/image_gen.py           — генерация картинок с seed
core/video_ai.py            — генерация видео (fal.ai + Ken Burns)
bot/handlers.py             — интеграция в бота
```

## Шаг 1: Подключение к серверу

### Вариант A: Через WinSCP/FileZilla
- Хост: `144.31.25.159`
- Пользователь: `root`
- Пароль: ваш текущий пароль от сервера
- Протокол: SFTP (порт 22)

### Вариант B: Через SSH (PowerShell/CMD)
```bash
ssh root@144.31.25.159
```

## Шаг 2: Бэкап (ОБЯЗАТЕЛЬНО!)

На сервере выполните:
```bash
cd /opt/ubt-farm
BACKUP_DIR="/opt/ubt-farm/backups/deploy_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp config/settings.py core/subtitle_timing.py video_engine/builder.py \
   core/llm_client.py core/image_gen.py core/video_ai.py bot/handlers.py \
   "$BACKUP_DIR/" 2>/dev/null || true
echo "Бэкап создан: $BACKUP_DIR"
```

## Шаг 3: Загрузка файлов

Замените файлы на сервере новыми версиями из папки `C:\Users\User\Desktop\убт\`:

**Путь на сервере:** `/opt/ubt-farm/`

| Локальный файл | Путь на сервере |
|---|---|
| config/settings.py | /opt/ubt-farm/config/settings.py |
| core/subtitle_timing.py | /opt/ubt-farm/core/subtitle_timing.py |
| video_engine/builder.py | /opt/ubt-farm/video_engine/builder.py |
| core/llm_client.py | /opt/ubt-farm/core/llm_client.py |
| core/image_gen.py | /opt/ubt-farm/core/image_gen.py |
| core/video_ai.py | /opt/ubt-farm/core/video_ai.py |
| bot/handlers.py | /opt/ubt-farm/bot/handlers.py |

## Шаг 4: Очистка кэша и перезапуск

На сервере выполните:
```bash
cd /opt/ubt-farm

# Удалить Python-кэш
rm -rf bot/__pycache__ config/__pycache__ core/__pycache__ video_engine/__pycache__

# Проверить синтаксис
./venv/bin/python3 -m py_compile config/settings.py core/subtitle_timing.py \
    video_engine/builder.py core/llm_client.py core/image_gen.py core/video_ai.py \
    bot/handlers.py && echo "COMPILE OK" || echo "COMPILE ERROR"

# Перезапустить ботов (если их два)
pm2 restart ubt-bot1 ubt-bot2

# Или только одного (если один бот)
pm2 restart ubt-bot1

# Посмотреть логи
pm2 logs ubt-bot1 --lines 30
```

## Что изменилось:

### Субтитры (не вылезают за края):
- Шрифт уменьшен: 72 → 68px
- MarginV увеличен: 420 → 500 (выше CTA-кнопки)
- MarginL/MarginR увеличены: 90 → 120 (для длинных слов)

### Картинки (уникальные):
- Каждая сцена получает уникальный seed
- Апскейл до 1080x1920 с Lanczos
- Цепочка Gemini → Pollinations

### Видео (качество):
- fal.ai queue API (правильный протокол)
- Ken Burns с разными движениями камеры
- Preset slow, CRF 18 (битрейт ~6Mbps вместо 1.5)

### Фолбэк-сцены (без повторов):
- Комбинаторная сборка из 6 пулов
- Гарантия уникальности при любом количестве сцен

## Если что-то пошло не так — откат:

```bash
cd /opt/ubt-farm
ls backups/  # найти последний бэкап
BACKUP_DIR="/opt/ubt-farm/backups/deploy_YYYYMMDD_HHMMSS"
cp "$BACKUP_DIR"/*.py . 2>/dev/null || true
pm2 restart ubt-bot1 ubt-bot2
```

## Проверка работы:

Отправьте боту @posts121212_bot команду `/generate` или любую команду, которая запускает создание видео. В логах должно появиться:

```
[OK] AI#1 Сценарий готов (N сцен)
[OK] AI#2 Картинка 1/N готова
[OK] AI#3 Видео 1/N готово
[OK] Готово: ubt_video_*.mp4
```

Если видите ошибки — проверьте `pm2 logs ubt-bot1` и пришлите вывод.
