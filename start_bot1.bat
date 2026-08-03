@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 🚀 Starting UBT Farm Bot 1 (оригинальный)...
python -m bot.run_bot --bot 1
pause
