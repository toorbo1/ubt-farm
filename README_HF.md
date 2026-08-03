---
title: UBT Video Generator
emoji: 🎬
colorFrom: purple
colorTo: blue
sdk: gradio
sdk_version: 4.44.1
app_file: web_app.py
pinned: false
license: mit
---

# 🎬 UBT Video Generator

Создание вирусных видео с помощью ИИ прямо в браузере!

## Возможности

-  **Генерация сценариев** через Gemini AI (Google AI Studio)
- 🖼️ **Pixel Art изображения** с enforced стилем (2D, cartoon, black cat)
- 🎥 **Видео assembly** через ffmpeg (local motion engine)
- 🔊 **TTS озвучка** через edge-tts
-  **Скачивание** готовых видео

## Настройка

### 1. Добавьте Gemini API ключ

Перейдите в Settings → введите ваш Gemini API ключ, или добавьте его в переменную окружения:

```
GEMINI_API_KEYS=AQ.xxx,AQ.yyy
```

Получить ключ: https://makersuite.google.com/app/apikey

### 2. Используйте

1. Вкладка **"Сценарий"**: введите тему → получите текст
2. Вкладка **"Видео"**: введите тему → получите готовое видео
3. Скачайте видео кнопкой под плеером

## Бесплатный деплой

### HuggingFace Spaces

1. Создайте Space: https://huggingface.co/new-space
2. Выберите SDK: Gradio
3. Загрузите файлы проекта
4. Добавьте секрет `GEMINI_API_KEYS` в Settings → Secrets

### Render.com

1. Fork репозиторий
2. Создайте Web Service на Render
3. Build Command: `pip install -r requirements_hf.txt`
4. Start Command: `python web_app.py`
5. Добавьте Environment Variable `GEMINI_API_KEYS`

## Локальный запуск

```bash
pip install -r requirements_hf.txt
python web_app.py
```

Откроется http://localhost:7860

## Ограничения бесплатного тарифа

- HF Spaces: 2 vCPU, 16GB RAM, засыпает после 48ч неактивности
- Render Free: 512MB RAM, засыпает после 15мин неактивности
- Gemini API: 60 запросов/мин бесплатно

## Лицензия

MIT
