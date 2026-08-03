#!/bin/bash
# Скрипт для настройки git на сервере (выполнить ОДИН РАЗ)
# После этого GitHub Actions сможет делать деплой

echo "=== Настройка git на сервере для автодеплоя ==="

cd /opt/ubt-farm

# Инициализация git если еще не инициализирован
if [ ! -d ".git" ]; then
    echo "Инициализация git репозитория..."
    git init
    git remote add origin <URL_ТВОЕГО_GITHUB_РЕПОЗИТОРИЯ>
fi

# Настройка ветки main
git branch -M main 2>/dev/null || true

echo ""
echo "✓ Git настроен в /opt/ubt-farm"
echo ""
echo "Следующие шаги:"
echo "1. Залей проект на GitHub (если еще не там)"
echo "2. Добавь secrets в GitHub репозиторий:"
echo "   - SSH_PRIVATE_KEY (приватный ключ для доступа к серверу)"
echo "   - SERVER_HOST (144.31.25.159)"
echo "   - SERVER_USER (root)"
echo ""
echo "Инструкция по созданию SSH ключа:"
echo "  ssh-keygen -t rsa -b 4096 -f ~/.ssh/deploy_key"
echo "  cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys"
echo "  cat ~/.ssh/deploy_key  # скопируй это в SSH_PRIVATE_KEY secret"
