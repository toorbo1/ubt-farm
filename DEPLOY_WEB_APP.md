# Деплой веб-приложения UBT Video Generator

## Вариант 1: HuggingFace Spaces (самый простой)

### Шаг 1: Создайте Space
1. Перейдите на https://huggingface.co/new-space
2. Выберите:
   - **Space name**: `ubt-video-generator` (или любое другое)
   - **License**: MIT
   - **SDK**: Gradio
   - **Visibility**: Public (бесплатно) или Private ($9/мес)

### Шаг 2: Загрузите файлы
Загрузите эти файлы в Space:
```
web_app.py
requirements_hf.txt
README_HF.md  (переименуйте в README.md)
core/gemini_client.py
core/image_gen.py
core/llm_client.py
core/tts_client.py
core/video_ai.py
core/ffmpeg_utils.py
core/motion.py
core/subtitle_timing.py
video_engine/builder.py
video_engine/*.py
config/settings.py
.env  (без реальных ключей!)
```

### Шаг 3: Добавьте секрет
1. В Space перейдите в **Settings → Secrets**
2. Добавьте секрет:
   - **Name**: `GEMINI_API_KEYS`
   - **Value**: ваш Gemini API ключ (из .env)

### Шаг 4: Готово!
Space автоматически запустится. URL будет вида:
```
https://huggingface.co/spaces/your-username/ubt-video-generator
```

---

## Вариант 2: Render.com (больше контроля)

### Шаг 1: Fork репозиторий
1. Создайте GitHub репозиторий с кодом проекта
2. Fork его (если нужно приватный)

### Шаг 2: Создайте Web Service
1. Перейдите на https://render.com
2. **New → Web Service**
3. Подключите GitHub репозиторий

### Шаг 3: Настройте сервис
```
Name: ubt-video-generator
Region: Frankfurt (ближе к России)
Branch: main
Root Directory: /
Runtime: Docker
Dockerfile: Dockerfile.render
```

### Шаг 4: Environment Variables
Добавьте переменные окружения:
```
GEMINI_API_KEYS=AQ.xxx,AQ.yyy
PORT=7860
```

### Шаг 5: Deploy
Нажмите **Create Web Service**.

Бесплатный тариф Render:
- 512MB RAM
- Засыпает после 15мин неактивности
- Просыпается за ~30сек при первом запросе

URL будет вида:
```
https://ubt-video-generator.onrender.com
```

---

## Вариант 3: Railway.app (альтернатива Render)

1. Перейдите на https://railway.app
2. **New Project → Deploy from GitHub**
3. Подключите репозиторий
4. Добавьте переменную `GEMINI_API_KEYS`
5. Deploy!

Railway даёт $5 кредитов бесплатно — хватает на ~200 часов работы.

---

## Вариант 4: Локальный сервер (для тестов)

```bash
cd C:\Users\User\Desktop\ubt_bot2
pip install -r requirements_hf.txt
python web_app.py
```

Откроется http://localhost:7860

Для доступа из интернета используйте ngrok:
```bash
ngrok http 7860
```

Получите временный URL вида `https://abc123.ngrok.app`

---

## Проверка работоспособности

После деплоя проверьте:

1.  **Вкладка "Сценарий"**: введите тему → должен появиться текст
2.  **Вкладка "Видео"**: введите тему → должно создаться видео (~1-3 мин)
3.  **Скачивание**: кнопка под видео должна работать

Если ошибки — проверьте логи в консоли Space/Render.

---

## Troubleshooting

**"No Gemini API keys configured"**
→ Добавьте `GEMINI_API_KEYS` в Secrets (HF) или Environment Variables (Render)

**"ffmpeg not found"**
→ Убедитесь что Dockerfile содержит `apt-get install -y ffmpeg`

**Space засыпает**
→ HF Spaces бесплатные засыпают через 48ч. Просто перезапустите.

**Видео не создаётся**
→ Проверьте что output_dir существует и доступен для записи
→ На Render файловая система ephemeral — видео удаляются при рестарте

**Медленная генерация**
→ Бесплатные тарифы имеют ограниченные CPU
→ Для ускорения используйте платный тариф или локальный запуск
