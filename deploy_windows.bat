@echo off
chcp 65001 >nul
title UBT Farm Deploy to 144.31.25.159
cd /d "%~dp0"

echo ===========================================
echo   Деплой UBT Farm на 144.31.25.159
echo ===========================================
echo.

:: Проверяем наличие pscp (из PuTTY) или scp
where pscp >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set SCP=pscp
) else (
    where scp >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set SCP=scp
    ) else (
        echo [✗] Найди scp (установи OpenSSH или PuTTY)
        pause
        exit /b 1
    )
)

set REMOTE_USER=root
set REMOTE_HOST=144.31.25.159
set REMOTE_DIR=/opt/ubt-farm

echo [1/4] Создаю директории на сервере...
plink -ssh %REMOTE_USER%@%REMOTE_HOST% "mkdir -p %REMOTE_DIR%/{bot,config,core,video_engine,uploader,uniqueizer,storage,assets/{backgrounds,fonts},output,logs,profiles}" < nul

echo [2/4] Копирую файлы проекта...
%SCP% -r -q ^
    --exclude .git ^
    --exclude __pycache__ ^
    --exclude .env ^
    --exclude output\*.mp4 ^
    * %REMOTE_USER%@%REMOTE_HOST%:%REMOTE_DIR%/

echo [3/4] Копирую deploy_on_server.sh...
%SCP% -q deploy_on_server.sh %REMOTE_USER%@%REMOTE_HOST%:/root/

echo [4/4] Запускаю установку на сервере...
plink -ssh %REMOTE_USER%@%REMOTE_HOST% "bash /root/deploy_on_server.sh"

echo.
echo ✅ Деплой завершён!
echo.
echo Проверь статус:   ssh %REMOTE_USER%@%REMOTE_HOST% "pm2 status"
echo Поправь .env:     ssh %REMOTE_USER%@%REMOTE_HOST% "nano %REMOTE_DIR%/.env"
echo.
pause
