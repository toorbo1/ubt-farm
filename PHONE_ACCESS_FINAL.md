# 📱 ПОЛНЫЙ ДОСТУП К САЙТУ С ТЕЛЕФОНА

## Вариант 1: Через локальную Wi-Fi сеть (самый простой)

### На ПК:
1. Узнай IP адрес ПК:
   ```powershell
   ipconfig | findstr IPv4
   ```
   Пример: `192.168.1.100`

2. Запусти сервер на порту 5001:
   ```bash
   cd "C:\Users\User\Desktop\убт"
   ./venv/Scripts/python.exe web_app/app.py --port 5001
   ```

### На телефоне:
1. Подключись к тому же Wi-Fi что и ПК
2. Открой браузер и введи: `http://192.168.1.100:5001`

---

## Вариант 2: Через ADB (USB подключение)

### На ПК:
1. Установи Android SDK Platform Tools
2. Включи "Отладку по USB" на телефоне
3. Выполни:
   ```bash
   adb devices  # проверить подключение
   adb reverse tcp:5001 tcp:5001  # проброс порта
   ```

4. Запусти сервер:
   ```bash
   cd "C:\Users\User\Desktop\убт"
   ./venv/Scripts/python.exe web_app/app.py --port 5001
   ```

### На телефоне:
Открой: `http://localhost:5001`

---

## Вариант 3: Через ngrok (HTTPS, работает отовсюду)

### На ПК:
1. Скачай ngrok: https://ngrok.com/download
2. Запусти туннель:
   ```bash
   ngrok http 5001
   ```
3. Получишь URL типа: `https://abc123.ngrok.io`

### На любом устройстве:
Открой этот URL — работает через интернет!

---

## Вариант 4: Установка прямо на телефон (Termux)

1. Скопируй файл `INSTALL_ON_PHONE.sh` на телефон
2. Установи Termux из F-Droid (НЕ Google Play!)
3. В Termux выполни:
   ```bash
   bash /sdcard/ubt-farm/INSTALL_ON_PHONE.sh
   source venv/bin/activate
   python web_app/app.py --port 5001
   ```
4. Открой: `http://localhost:5001`

---

## 🔑 API Ключи (уже настроены):

- **LLM**: `sk-smart-_0uezNrlxMhc4zZGmjZQpdAZl8adsHe2KpFgaFzcIKs`
- **Pollinations** (картинки): бесплатно, без ключа
- **Cloudflare R2** (хранилище): нужно настроить для 10GB

---

## Готовые файлы для деплоя:

- `INSTALL_ON_PHONE.sh` — скрипт установки на телефон
- `DEPLOY_TO_PHONE.bat` — автоматический деплой через ADB
- `START_SERVER_WITH_NGROK.bat` — запуск с ngrok туннелем
- `TERMUX_CONSOLE.txt` — команды для Termux

Выбери удобный способ и пользуйся! 🎉
