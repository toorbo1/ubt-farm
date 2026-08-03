@echo off
echo ========================================
echo  Деплой UBT Farm на телефон через ADB
echo ========================================
echo.

:: Проверка ADB
where adb >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] ADB не найден!
    echo.
    echo Установи Android SDK Platform Tools:
    echo https://developer.android.com/tools/releases/platform-tools
    echo.
    pause
    exit /b
)

:: Проверка подключения телефона
echo [1/4] Проверка подключения телефона...
adb devices | findstr device >nul
if %errorlevel% neq 0 (
    echo [ОШИБКА] Телефон не подключен!
    echo.
    echo Включи "Отладку по USB" в настройках телефона
    echo и подключи кабель USB к ПК
    pause
    exit /b
)

echo [OK] Телефон подключен

:: Копирование файлов
echo [2/4] Копирование файлов проекта...
adb push web_app /sdcard/ubt-farm/web_app
adb push .env /sdcard/ubt-farm/.env
adb push requirements.txt /sdcard/ubt-farm/requirements.txt

echo [3/4] Установка прав на скрипты...
adb shell "chmod +x /sdcard/ubt-farm/INSTALL_ON_PHONE.sh"

echo [4/4] Запуск установки на телефоне...
adb shell "cd /sdcard/ubt-farm && bash INSTALL_ON_PHONE.sh"

echo.
echo ========================================
echo  ДЕПЛОЙ ЗАВЕРШЁН!
echo ========================================
echo.
echo Теперь на телефоне выполни:
echo   cd /sdcard/ubt-farm
echo   source venv/bin/activate
echo   python web_app/app.py --port 5001
echo.
pause
