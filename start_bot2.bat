@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 🚀 Starting UBT Farm Bot 2 (новый)...
python -m bot.run_bot --bot 2
pause
