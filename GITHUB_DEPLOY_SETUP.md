# Настройка автоматического деплоя через GitHub Actions

## Шаг 1: Залить проект на GitHub

```bash
cd C:\Users\User\Desktop\убт

# Если репозиторий еще не создан на GitHub:
git remote add origin https://github.com/ТВОЙ_USERNAME/ТВОЙ_РЕПОЗИТОРИЙ.git

# Или если уже есть:
git remote set-url origin https://github.com/ТВОЙ_USERNAME/ТВОЙ_РЕПОЗИТОРИЙ.git

git add .
git commit -m "Setup auto-deploy with GitHub Actions"
git push -u origin main
```

## Шаг 2: Создать SSH ключ для доступа к серверу

На **локальной машине** (Windows):

```powershell
# Открой PowerShell и выполни:
ssh-keygen -t rsa -b 4096 -f C:\Users\User\.ssh\deploy_key

# Не добавляй passphrase (просто нажми Enter)
```

После этого:
1. Публичный ключ добавь на сервер:
   ```bash
   # Скопируй содержимое файла C:\Users\User\.ssh\deploy_key.pub
   # И добавь его в /root/.ssh/authorized_keys на сервере
   ```

2. Приватный ключ скопируй целиком:
   ```bash
   type C:\Users\User\.ssh\deploy_key
   ```

## Шаг 3: Добавить secrets в GitHub репозиторий

Зайди в свой GitHub репозиторий → Settings → Secrets and variables → Actions → New repository secret

Добавь три секрета:

1. **SSH_PRIVATE_KEY**
   - Вставь содержимое файла `C:\Users\User\.ssh\deploy_key` (весь приватный ключ)

2. **SERVER_HOST**
   - Значение: `144.31.25.159`

3. **SERVER_USER**
   - Значение: `root`

## Шаг 4: Настроить git на сервере (ОДИН РАЗ)

Подключись к серверу и выполни:

```bash
ssh root@144.31.25.159

cd /opt/ubt-farm
git init
git remote add origin https://github.com/ТВОЙ_USERNAME/ТВОЙ_РЕПОЗИТОРИЙ.git
git fetch origin main
git reset --hard origin/main
git branch --set-upstream-to=origin/main main
```

## Шаг 5: Протестировать деплой

```bash
cd C:\Users\User\Desktop\убт

# Сделай любое изменение
echo "# Test deploy" >> README.md

git add .
git commit -m "Test auto-deploy"
git push
```

GitHub Actions автоматически задеплоит изменения на сервер! 🚀

## Проверка статуса деплоя

Зайди в GitHub репозиторий → Actions → увидишь running workflow → кликай на него → смотри логи

## Откат изменений

Если что-то сломалось:

```bash
# На сервере:
cd /opt/ubt-farm
ls backups/  # найти последний бекап
BACKUP_DIR="/opt/ubt-farm/backups/deploy_YYYYMMDD_HHMMSS"
cp -r "$BACKUP_DIR"/* .
pm2 restart ubt-bot1 ubt-bot2
```
