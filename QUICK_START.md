# ⚡ БЫСТРЫЙ СТАРТ - Все ссылки

## 📱 Termux на телефоне

1. **Установить Termux** (из F-Droid, НЕ Google Play!)
   - Скачать: https://f-droid.org/packages/com.termux/

2. **Настройка:**
   ```bash
   pkg update && pkg upgrade
   pkg install python git ffmpeg
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python bot/run_bot.py --bot 1
   ```

3. **Подробная инструкция:** [TERMUX_SETUP.md](TERMUX_SETUP.md)

---

## 🌐 Бесплатный хостинг 24/7

### Koyeb.com (рекомендуется)
- ✅ Бесплатно навсегда
- ✅ Не засыпает
- ✅ 2 GB RAM
- ✅ Python + FFmpeg

**Инструкция:** [koyeb-deploy.md](koyeb-deploy.md)

### Render.com
- ⚠️ Засыпает после 15 мин неактивности
- ✅ 750 часов/месяц бесплатно

---

## 🖥 Локальное тестирование

```bash
cd "C:\Users\User\Desktop\убт"
python test_quality_app.py
```

Приложение покажет:
- 📝 Полный текст сценария
- 🖼 Картинки в галерее
- 🎬 Видео после генерации

---

## 📚 Документация

- **Сайт-документация:** Открой `docs/index.html` в браузере
- **Полный гайд:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **README для GitHub:** [README.md](README.md)

---

## 🔧 Что уже настроено

✅ **API ключи** — все в `.env`, работают из коробки
✅ **Генерация картинок** — Pollinations.ai (бесплатно, без ключа)
✅ **Генерация видео** — Ken Burns (локально) или fal.ai
✅ **Сценарии** — комбинаторные промпты, без повторов
✅ **Субтитры** — ASS формат, правильные координаты

---

## 🚀 Деплой за 5 минут

1. Зарегистрироваться на [Koyeb.com](https://www.koyeb.com/)
2. Нажать "Create Service" → "Deploy from Git"
3. Добавить переменные окружения из `.env`
4. Deploy!

Бот будет работать 24/7 бесплатно!

---

## 📞 Если что-то не работает

1. Проверь логи: `pm2 logs ubt-bot1`
2. Проверь .env переменные
3. Перезапусти: `pm2 restart ubt-bot1`

Все файлы готовы к деплою! 🎉
