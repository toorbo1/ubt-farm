# PowerShell скрипт для деплоя на сервер blobby_penguin (144.31.25.159)

$serverIP = "144.31.25.159"
$username = "root"
$remotePath = "/opt/ubt-farm/"
$localArchive = "C:\Users\User\Desktop\убт\ubt_deploy_20260803_112611.tar.gz"

Write-Host "=== Деплой на сервер $serverIP ===" -ForegroundColor Green

# Проверяем существование архива
if (-not (Test-Path $localArchive)) {
    Write-Host "❌ Архив не найден: $localArchive" -ForegroundColor Red
    exit 1
}

Write-Host "📦 Архив: $(Split-Path $localArchive -Leaf)" -ForegroundColor Cyan
Write-Host "📍 Сервер: $serverIP" -ForegroundColor Cyan
Write-Host ""

# Копируем архив на сервер
Write-Host "⬆️ Загрузка архива на сервер..." -ForegroundColor Yellow

try {
    # Используем scp через PowerShell
    & scp -o StrictHostKeyChecking=no $localArchive "${username}@${serverIP}:${remotePath}"

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Архив загружен успешно!" -ForegroundColor Green
    } else {
        throw "scp failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Host "❌ Ошибка загрузки: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Попробуй ручной способ:" -ForegroundColor Yellow
    Write-Host "1. Открой WinSCP или FileZilla" -ForegroundColor White
    Write-Host "2. Подключись к $serverIP" -ForegroundColor White
    Write-Host "3. Загрузи файл: $localArchive" -ForegroundColor White
    Write-Host "4. На сервере выполни команды из deploy_commands.txt" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "=== Следующие шаги ===" -ForegroundColor Green
Write-Host "1. Подключись к серверу по SSH (если есть доступ)" -ForegroundColor White
Write-Host "2. Или используй веб-консоль хостинга" -ForegroundColor White
Write-Host "3. Выполни команды из файла deploy_commands.txt" -ForegroundColor White
Write-Host ""

# Создаем файл с командами для сервера
$commands = @"
# Команды для выполнения на сервере после загрузки архива
cd /opt/ubt-farm
tar xzf ubt_deploy_*.tar.gz
rm -rf bot/__pycache__ core/__pycache__ video_engine/__pycache__
pm2 restart ubt-bot1 ubt-bot2
pm2 logs ubt-bot1 --lines 30
"@

$commands | Out-File -FilePath "C:\Users\User\Desktop\убт\deploy_commands.txt" -Encoding UTF8
Write-Host "✅ Создан файл deploy_commands.txt с командами для сервера" -ForegroundColor Green
