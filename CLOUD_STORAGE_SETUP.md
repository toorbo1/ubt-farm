# ☁️ Настройка Cloudflare R2 (бесплатное хранилище 10 GB)

## Шаг 1: Регистрация

1. Перейди на [Cloudflare.com](https://www.cloudflare.com/)
2. Нажми "Sign Up" (бесплатно)
3. Подтверди email

## Шаг 2: Создание R2 Bucket

1. Зайди в Dashboard → **R2 Storage**
2. Нажми **"Create Bucket"**
3. Имя: `ubt-media`
4. Region: **Auto** (ближайший к тебе)

## Шаг 3: Получение ключей API

1. В R2 Dashboard нажми **"Manage R2 API Tokens"**
2. Нажми **"Create API Token"**
3. Выбери шаблон: **"Admin Read & Write"**
4. Скопируй:
   - **Access Key ID**
   - **Secret Access Key**
   - **Account ID** (в URL страницы)

## Шаг 4: Добавление переменных окружения

Добавь в `.env`:

```env
# Cloudflare R2 Storage
R2_ACCOUNT_ID=abc123def456
R2_ACCESS_KEY=your_access_key_here
R2_SECRET_KEY=your_secret_key_here
R2_BUCKET_NAME=ubt-media
```

## Шаг 5: Установка зависимостей

```bash
cd "C:\Users\User\Desktop\убт"
./venv/Scripts/pip.exe install boto3
```

## Шаг 6: Перезапуск сервера

Сервер автоматически запустит фоновую очистку старых файлов.

## 🎁 Бесплатный лимит:

- ✅ **10 GB** хранилища бесплатно
- ✅ **Без лимита** на исходящий трафик (!)
- ✅ Автоматическая очистка каждые 24 часа
- ✅ Файлы хранятся 24 часа, потом удаляются

## 🔧 Без настройки R2:

Если R2 не настроен, файлы сохраняются локально в `test_output/` и тоже очищаются каждые 24 часа.

## Проверка работы:

Открой веб-приложение → Галерея → должны показаться файлы из облака.

---

**Готово!** Хранилище работает с авто-очисткой! 🎉
