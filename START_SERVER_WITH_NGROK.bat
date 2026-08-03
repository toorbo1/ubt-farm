@echo off
echo ========================================
echo  UBT Farm - Запуск сервера + Ngrok
echo ========================================
echo.

:: Проверка ngrok
where ngrok >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Ngrok не найден!
    echo.
    echo Установи ngrok:
    echo 1. Скачай с https://ngrok.com/download
    echo 2. Распакуй в эту же папку
    echo.
    pause
    exit /b
)

:: Запуск Flask сервера
echo [1/3] Запускаю Flask сервер на порту 5001...
start "" cmd /k "cd /d "%~dp0" && ./venv/Scripts/python.exe web_app/app.py --port 5001"
timeout /t 3 >nul

:: Запуск ngrok
echo [2/3] Запускаю ngrok туннель...
start "" cmd /k "ngrok http 5001"
timeout /t 5 >nul

:: Получение URL
echo [3/3] Открываю браузер с инструкцией...
echo.
echo ========================================
echo  СЕРВЕР ЗАПУЩЕН!
echo ========================================
echo.
echo Локально: http://localhost:5001
echo.
echo Ngrok URL откроется в браузере через несколько секунд.
echo Этот URL работает отовсюду — с телефона, планшета, любого ПК!
echo.
echo Для Termux на телефоне смотри файл: TERMUX_INSTRUCTIONS.txt
echo.
pause
