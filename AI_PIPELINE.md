# AI Pipeline — Как работают 3 ИИ вместе

## 🏗️ Архитектура системы

Система состоит из **трёх независимых ИИ**, работающих последовательно:

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│   ИИ #1     │ ───▶ │   ИИ #2      │ ───▶ │   ИИ #3      │
│   Gemini    │      │   Изображения│      │   Видео      │
│   (Текст)   │      │   (Картинки) │      │   (Анимация) │
└─────────────┘      └──────────────┘      └──────────────┘
```

---

## 🤖 ИИ #1 — Google Gemini (Текст и Сценарии)

**Файл**: `core/gemini_client.py`

### Что делает:
1. Генерирует вирусные тексты для TikTok/Reels/Shorts
2. Разбивает текст на 3-5 сцен
3. Для каждой сцены создаёт:
   - **narration** — текст озвучки (русский, 15-30 слов)
   - **image_prompt** — детальное описание для генератора изображений (английский, 50-80 слов)
   - **video_prompt** — описание движения для анимации (английский, 30-50 слов)

### Пример output:
```json
{
  "scenes": [
    {
      "narration": "Представьте: **общественный Wi-Fi** как стеклянный дом...",
      "image_prompt": "2D pixel art, 16-bit retro game aesthetic, cartoon style. A cute small black pixel cat with glowing green eyes sitting in transparent glass house made of WiFi signals...",
      "video_prompt": "Slow camera pan across transparent walls showing data streams flowing through them. Cat gestures toward invisible network traffic. Subtle glow effects from digital signals.",
      "duration": 3
    }
  ]
}
```

### API ключ:
Находится в `.env` → `LLM_API_KEY=AQ.Ab8RN6IxzM4_1uRShXgeB9kDR3Zy-YZdge36FwDvEJxhXFUpHg`

---

## 🎨 ИИ #2 — Генерация Изображений

**Файл**: `core/image_gen.py`

### Доступные провайдеры (в порядке приоритета):
1. **Gemini Image** (Google) — высокое качество, ротация ключей
2. **Pollinations.ai** — бесплатный, без API-ключа
3. **Stability AI (SD3.5)** — профессиональное качество
4. **OpenAI DALL-E 3** — запасной вариант
5. **HuggingFace Inference** (FLUX.1, SDXL)
6. **Replicate** (SDXL/FLUX)
7. **Local Fallback Generator** — полностью офлайн, рисует pixel-art через PIL

### Что получает от ИИ #1:
```
image_prompt = "2D pixel art, 16-bit retro game aesthetic, cartoon style.
A cute small black pixel cat with glowing green eyes sitting cross-legged on a floating holographic keyboard...
Low-angle hero shot, dramatic rim lighting, vibrant cyan and magenta palette.
9:16 vertical portrait, no text, no watermark, no logo."
```

### Что производит:
- Изображение 1080x1920 (9:16 вертикальный формат)
- Автоматический AI upscale до целевого разрешения
- Улучшение качества: sharpening, denoising, enhancement

---

## 🎬 ИИ #3 — Анимация (Image-to-Video)

**Файл**: `core/video_ai.py`

### Доступные провайдеры (цепочка с fallback):
1. **fal.ai** (Kling AI) — быстрая генерация видео
2. **Runway Gen-3 Alpha** — профессиональное качество
3. **Pika Labs** — стильные эффекты
4. **Replicate** (Stable Video Diffusion) — локальная генерация с GPU
5. **Local Motion Engine** — всегда доступен, Ken Burns эффекты через ffmpeg

### Что получает от ИИ #1:
```
video_prompt = "Slow camera zoom toward cat's face. Cat looks up from keyboard, ears perk up.
Code continues scrolling on background monitors. Floating data particles drift lazily upward.
Smooth, contemplative motion."
```

### Что производит:
- Видео клип 1080x1920 @ 30fps
- Длительность соответствует `duration` из сценария
- Валидация на реальные кадры и длительность

---

## 🔧 Видео-движок (Сборка)

**Файл**: `video_engine/builder.py`

### Что делает:
1. Получает сценарий от ИИ #1 (список сцен)
2. Для каждой сцены:
   - Вызывает ИИ #2 → генерирует изображение по `image_prompt`
   - Вызывает ИИ #3 → анимирует изображение по `video_prompt`
3. Генерирует TTS озвучку (Edge TTS или ElevenLabs)
4. Создаёт ASS субтитры с подсветкой ключевых слов
5. Монтирует финальное видео:
   - Объединяет все клипы
   - Накладывает аудио дорожку
   - Добавляет CTA-кнопку в конце
   - Применяет переходы между сценами

---

## 📊 Полный пайплайн

```
Пользователь: "Хочу видео про VPN"
       │
       ▼
┌─────────────────┐
│  ИИ #1: Gemini  │  Генерирует сценарий из 3-5 сцен
└─────────────────┘  с промптами для изображений и видео
       │
       ├──▶ narration[0]: "Представьте: общественный Wi-Fi..."
       ├──▶ image_prompt[0]: "2D pixel art, 16-bit..."
       ├──▶ video_prompt[0]: "Slow camera zoom..."
       │
       ▼
┌──────────────────────┐
│  ИИ #2: Изображения  │  Для каждого image_prompt
└──────────────────────┘
       │
       ├──▶ scene_0.png (1080x1920)
       ├──▶ scene_1.png (1080x1920)
       ├──▶ scene_2.png (1080x1920)
       │
       ▼
┌─────────────────────┐
│  ИИ #3: Видео       │  Для каждой пары (image, video_prompt)
└─────────────────────┘
       │
       ├──▶ clip_0.mp4 (3 сек)
       ├──▶ clip_1.mp4 (3 сек)
       ├──▶ clip_2.mp4 (3 сек)
       │
       ▼
┌─────────────────────┐
│  Video Engine       │  Сборка + TTS + субтитры + CTA
└─────────────────────┘
       │
       ▼
  output/final_video.mp4
```

---

## 🎯 Пример детальных промптов

### От ИИ #1 для ИИ #2 (изображение):
```
2D pixel art, 16-bit retro game aesthetic, cartoon style.
A cute small black pixel cat with glowing green eyes standing confidently on hind legs,
holding oversized golden key like a sword, defensive stance in front of massive steel vault door with digital keypad.
Background shows shadowy figures with question marks trying to approach but blocked by glowing shield barrier.
Night time urban rooftop setting with neon-lit skyscrapers in distance.
Wide establishing shot, spotlight on cat and vault, dramatic contrast.
Color palette: metallic silver, warning red, security green.
Details: binary code raining in background, padlock icons floating, spark effects where shield meets shadows.
Pixel-perfect precision, clean anti-aliased edges.
9:16 vertical portrait, no text, no watermark, no logo.
```

### От ИИ #1 для ИИ #3 (видео):
```
Camera circles around cat in slow arc. Cat gestures dramatically with paw toward vault door, tail swishing for emphasis.
Golden key glows brighter when mentioned. Shadowy figures in background retreat slowly.
Shield barrier pulses with protective energy. Dynamic, confident movement with clear focal points.
```

---

## 🚀 Запуск

### Быстрый тест:
```bash
cd "C:\Users\User\Desktop\убт"
python test_quality_app.py
```

### Генерация видео:
```bash
python main.py build --topic "кибербезопасность"
```

### Через Telegram бота:
```
/start → Создать сценарий → Выбрать тему
```

---

## 📝 Ключевые файлы

| Файл | Описание |
|------|----------|
| `core/gemini_client.py` | Клиент для Gemini API (ИИ #1) |
| `core/image_gen.py` | Генераторы изображений (ИИ #2) |
| `core/video_ai.py` | Генераторы видео (ИИ #3) |
| `core/llm_client.py` | Системные промпты и fallback логика |
| `video_engine/builder.py` | Сборка финального видео |
| `GEMINI_SETUP.md` | Настройка Gemini API |

---

## 💡 Советы по качеству

### Для лучших изображений (ИИ #2):
- Промпт должен быть 50-80 слов
- Обязательно указывать: стиль, персонажа, действие, локацию, освещение, цвета
- Добавлять 3-5 деталей окружения
- Всегда заканчивать на "9:16 vertical portrait, no text, no watermark, no logo"

### Для лучшей анимации (ИИ #3):
- Описывать конкретные движения камеры
- Указывать действия персонажа (моргание, движение хвоста)
- Добавлять движение фона (частицы, неон, дождь)
- Включать атмосферные эффекты (grain, lens flare, light rays)

### Для лучших текстов (ИИ #1):
- Тема должна быть конкретной ("VPN для общественных сетей" лучше чем просто "VPN")
- Можно указать стиль/черты ("научный", "юмористический", "драматичный")
- Gemini автоматически выделит 2-4 ключевых слова для визуального акцента
