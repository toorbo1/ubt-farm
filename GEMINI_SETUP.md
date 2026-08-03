# Настройка Google Gemini API (ИИ #1)

## 🔑 API Ключ

**Ключ**: `AQ.Ab8RN6IxzM4_1uRShXgeB9kDR3Zy-YZdge36FwDvEJxhXFUpHg`

Ключ настроен в двух местах:
- `.env` → `LLM_API_KEY`
- `config/settings.py` → `llm_api_key` (значение по умолчанию)

## 🎯 Что делает ИИ #1 (Gemini)

Google Gemini — это **основной мозг системы**, отвечающий за генерацию креативного контента. Он создаёт:

### 1️⃣ **Тексты для озвучки**
- Вирусные сценарии на 15-30 секунд
- Цепляющие hook'и (первые 3 секунды)
- Призывы к действию (CTA)
- Выделение ключевых слов через `**звёздочки**`

### 2️⃣ **Промпты для ИИ #2 (Изображения)**
Для каждой сцены Gemini пишет детальное описание на английском (50-80 слов):
```
2D pixel art, 16-bit retro game aesthetic, cartoon style.
A cute small black pixel cat with glowing green eyes sitting cross-legged on a floating holographic keyboard...
Low-angle hero shot, dramatic rim lighting, vibrant cyan and magenta palette.
9:16 vertical portrait, no text, no watermark, no logo.
```

### 3️⃣ **Промпты для ИИ #3 (Видео/Анимация)**
Для каждой сцены Gemini описывает движение на английском (30-50 слов):
```
Slow camera zoom toward cat's face. Cat looks up from keyboard, ears perk up.
Code continues scrolling on background monitors. Floating data particles drift lazily upward.
Smooth, contemplative motion.
```

## 📊 Модель

- **Модель**: `gemini-2.5-flash`
- **Base URL**: `https://generativelanguage.googleapis.com/v1beta/models`
- **Temperature**: 0.8 для текстов, 0.95 для сценариев
- **Max Tokens**: 500 для текстов, 2000 для сценариев

## 🔄 Процесс работы

1. Пользователь задаёт тему (например, "VPN и приватность")
2. Gemini генерирует цепляющий текст (40-70 слов)
3. Gemini разбивает текст на 3-5 сцен
4. Для каждой сцены создаются:
   - `narration` — текст озвучки (русский)
   - `image_prompt` — промпт для генерации изображения (английский, 50-80 слов)
   - `video_prompt` — промпт для анимации (английский, 30-50 слов)
5. Промпты передаются в ИИ #2 и ИИ #3

## 🛠️ Файлы

- `core/gemini_client.py` — клиент для Gemini API
- `core/llm_client.py` — улучшенные системные промпты
- `core/llm_client_gemini.py` — альтернативная реализация

## ✅ Проверка работы

Запусти тестовое приложение:
```bash
python test_quality_app.py
```

Или сгенерируй видео через консоль:
```bash
python main.py build --topic "кибербезопасность"
```

## 💡 Советы

- Gemini работает без ротации ключей (один ключ в `.env`)
- Если ключ не работает — проверь баланс в Google AI Studio
- Для офлайн-режима есть fallback на комбинаторные промпты
