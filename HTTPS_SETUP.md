# 🔒 Настройка HTTPS доступа для всех устройств

## Проблема:
Локальный сервер `http://localhost:5001` доступен только на ПК.
Нужен HTTPS чтобы открывать с телефона/планшета/других ПК.

## Решение 1: Ngrok (самый простой)

### Шаг 1: Установи ngrok
Скачай с https://ngrok.com/download

### Шаг 2: Запусти туннель
```bash
ngrok http 5001
```

### Шаг 3: Получишь HTTPS URL
Пример: `https://abc123.ngrok.io`

Этот URL работает отовсюду! 🌍

---

## Решение 2: Cloudflare Tunnel (бесплатно, постоянно)

### Шаг 1: Установи cloudflared
```bash
# Windows (через Chocolatey)
choco install cloudflared

# Или скачай бинарник:
# https://github.com/cloudflare/cloudflared/releases
```

### Шаг 2: Создай туннель
```bash
cloudflared tunnel --url http://localhost:5001
```

### Шаг 3: Получишь *.trycloudflare.com URL
Работает бесплатно без ограничений!

---

## Решение 3: Локальная сеть (только Wi-Fi)

### На ПК:
Узнай IP: `ipconfig | findstr IPv4` → например `192.168.1.100`

### На телефоне:
Открой: `http://192.168.1.100:5001`

⚠️ Работает только в одной Wi-Fi сети!

---

## Рекомендация:
Используй **ngrok** — проще всего, работает везде, бесплатно!
