@echo off
echo ========================================
echo  UBT Farm - Запуск с HTTPS доступом
echo ========================================
echo.

:: Убить старые процессы
taskkill /F /IM python.exe 2>nul

:: Запустить единый сайт
echo [1/3] Запускаю сайт на порту 5001...
start "" cmd /k "cd /d "%~dp0" && ./venv/Scripts/python.exe web_app/unified.py --port 5001"
timeout /t 3 >nul

:: Проверить ngrok
where ngrok >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Ngrok не найден!
    echo.
    echo Для HTTPS доступа установи ngrok:
    echo https://ngrok.com/download
    echo.
    echo Без ngrok сайт доступен только локально:
    echo http://localhost:5001
    echo.
    pause
    exit /b
)

:: Запустить ngrok
echo [2/3] Запускаю ngrok туннель...
start "" cmd /k "ngrok http 5001"
timeout /t 5 >nul

echo [3/3] Открываю браузер...
start http://localhost:5001

echo.
echo ========================================
echo  САЙТ ЗАПУЩЕН!
echo ========================================
echo.
echo Локально: http://localhost:5001
echo.
echo Ngrok URL откроется в новом окне — скопируй его
echo и поделись с кем угодно! Работает отовсюду!
echo.
pause
