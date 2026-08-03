# Настройка Termux на Android

## Установка Termux

⚠️ **ВАЖНО:** Устанавливай ТОЛЬКО из F-Droid, НЕ из Google Play!

1. Скачать F-Droid: https://f-droid.org/
2. Установить F-Droid APK
3. Открыть F-Droid → поиск "Termux"
4. Установить Termux

## Первоначальная настройка

Открыи Termux и выполни:

```bash
# Обновить все пакеты
pkg update && pkg upgrade

# Дать разрешение на доступ к хранилищу
termux-setup-storage

# Установить Python и зависимости
pkg install python git ffmpeg openssh wget

# Проверить версии
python --version
ffmpeg -version
```

## Клонирование проекта

```bash
# Создать директорию
mkdir -p ~/projects
cd ~/projects

# Клонировать (если есть GitHub)
git clone https://github.com/<username>/ubt-farm.git
cd ubt-farm

# ИЛИ скопировать файлы с телефона
# Если проект на ПК, используй adb:
# На ПК: adb push C:\Users\User\Desktop\убт /sdcard/projects/
```

## Настройка виртуального окружения

```bash
cd ~/projects/ubt-farm

# Создать venv
python -m venv venv

# Активировать
source venv/bin/activate

# Обновить pip
pip install --upgrade pip

# Установить зависимости
pip install -r requirements.txt
```

## Запуск бота

```bash
cd ~/projects/ubt-farm
source venv/bin/activate

# Запустить бота #1
python bot/run_bot.py --bot 1

# Или бота #2
python bot/run_bot.py --bot 2
```

## Автозапуск при старте Termux

Создать файл `~/.termux/boot/start-ubt.sh`:

```bash
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-ubt.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd /data/data/com.termux/files/home/projects/ubt-farm
source venv/bin/activate
python bot/run_bot.py --bot 1
EOF

chmod +x ~/.termux/boot/start-ubt.sh
```

## Подключение к ПК через ADB

**На ПК:**
```bash
# Включить USB-отладку на телефоне
# Настройки → О телефоне → 7 раз нажать "Номер сборки"
# Затем: Настройки разработчика → USB-отладка

# Подключить телефон по USB
adb devices

# Подключить по WiFi (первый раз по USB)
adb tcpip 5555
adb connect <IP_телефона>:5555
```

**Теперь можно запускать команды с ПК:**
```bash
adb shell "cd ~/projects/ubt-farm && source venv/bin/activate && python bot/run_bot.py --bot 1"
```

## Полезные команды

```bash
# Посмотреть логи
tail -f logs/bot-out.log

# Проверить процессы
ps aux | grep python

# Остановить бота
killall python

# Посмотреть использование памяти
top
```

## Проблемы

**ModuleNotFoundError:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Permission denied:**
```bash
chmod +x ~/.termux/boot/start-ubt.sh
```

**FFmpeg не найден:**
```bash
pkg install ffmpeg
```
