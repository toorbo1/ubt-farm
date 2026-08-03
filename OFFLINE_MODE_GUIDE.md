# Офлайн-режим UBT Bot 2

## Что работает без сервера

| Компонент | Статус | Детали |
|-----------|--------|--------|
| Gemini API (сценарии) | ✅ Работает | Использует GEMINI_API_KEYS из .env |
| Генерация изображений | ✅ Работает | Pollinations (онлайн) + Local fallback (офлайн) |
| TTS (озвучка) | ✅ Работает | edge-tts, не требует ключа |
| Видео (motion engine) | ✅ Работает | Локальный ffmpeg, не требует API |
| Сборка видео | ✅ Работает | ffmpeg CRF 18, preset medium |
| VPN монитор | ❌ Не работает | Требует сервер на порту 8443 |

## Запуск офлайн-режима

### 1. Проверка зависимостей
```bash
cd C:\Users\User\Desktop\ubt_bot2
python offline_mode.py --check
```

### 2. Тест полного пайплайна
```bash
python offline_mode.py --test
```
Создаёт тестовое видео на тему "VPN безопасность".

### 3. Интерактивный режим
```bash
python offline_mode.py --interactive
```
Вводите тему → получаете готовое видео.

### 4. Через Telegram бота
```bash
python -m bot.run_bot --bot 1
```
Бот работает полностью локально (кроме Gemini API для сценариев).

## Архитектура офлайн-режима

```
┌─────────────────────────────────────────────────────┐
│                  Пользователь                        │
│         (Telegram или CLI интерактив)                │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────
│              GeminiClient (AI #1)                    │
│  - generate_script(topic, traits)                    │
│  - break_into_scenes(script_text)                    │
│  - regenerate_script(old_text, topic, traits)        │
│  Ключи: GEMINI_API_KEYS из .env                      │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│           ChainImageGenerator (AI #2)                │
│  1. GeminiImageGenerator (если есть ключи)           │
│  2. PollinationsImageGenerator (бесплатно)           │
│  3. LocalFallbackGenerator (pixel art, офлайн)       │
│  Все промпты: _enforce_pixel_art_style()             │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│          ChainImageToVideoGenerator (AI #3)          │
│  1. FalAI (если есть FAL_API_KEY)                    │
│  2. Replicate (если есть REPLICATE_API_KEY)          │
│  3. LocalMotionGenerator (ffmpeg, всегда)            │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              TTSClient (edge-tts)                    │
│  - synthesize_scene(text, output_path)               │
│  - WordBoundary timing для субтитров                 │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│           VideoBuilder (сборка)                      │
│  1. TTS → audio.wav                                  │
│  2. Image gen → scene_N.jpg                          │
│  3. Video gen → scene_video_N.mp4                    │
│  4. ffmpeg assembly → final video                    │
└─────────────────────────────────────────────────────┘
```

## Обязательные условия для изображений

Функция `_enforce_pixel_art_style()` гарантирует наличие:
- **"2D"** — двумерный формат
- **"pixel art"** — пиксельная графика
- **"cartoon style"** — мультяшный стиль
- **"a cute small black pixel cat with glowing green eyes"** — персонаж

Пример enforced промпта:
```
2D, pixel art, cartoon style, a cute small black pixel cat with glowing green eyes,
a cute small black pixel cat sitting on keyboard, in hacker den, low-angle shot,
dramatic rim lighting, vibrant cyan and magenta palette, 9:16 vertical portrait
```

## Настройка .env для офлайн-режима

```env
# Обязательно — Gemini для сценариев
GEMINI_API_KEYS=AQ.Ab8RN6Is7YzkaELKqx1Hn-IR30pEPtcT5ias4EmkruinZzVMTA,...

# Опционально — для улучшения качества изображений (онлайн)
# OPENROUTER_API_KEY=sk-or-v1-...
# FAL_API_KEY=...
# REPLICATE_API_KEY=...

# TTS — не требует настроек (edge-tts)
TTS_ENGINE=edge

# Видео — local motion engine всегда доступен
USE_AI_VIDEO=true
```

## Ограничения офлайн-режима

1. **Gemini API требует интернет** — без него сценарии не генерируются
   - Решение: использовать `_default_scenes()` из llm_client.py (комбинаторные шаблоны)
2. **Pollinations требует интернет** — без него fallback на LocalFallbackGenerator
   - LocalFallbackGenerator создаёт простые pixel art спрайты программно
3. **fal.ai/replicate требуют API ключи** — без них fallback на LocalMotionGenerator
   - LocalMotionGenerator создаёт Ken Burns эффект через ffmpeg

## Полностью офлайн (без интернета вообще)

Для работы без любого интернета:

1. В `core/llm_client.py` измените `generate_scenes()`:
```python
async def generate_scenes(self, topic: Optional[str] = None) -> dict:
    # Всегда использовать комбинаторный фолбэк
    return self._default_scenes(topic)
```

2. В `core/image_gen.py` измените `get_image_generator()`:
```python
def get_image_generator() -> ImageGenerator:
    return LocalFallbackGenerator()  # Только локальная генерация
```

3. Убедитесь что ffmpeg установлен:
```bash
# Windows — используйте platform-tools из проекта
./platform-tools/ffmpeg.exe -version
```

## Troubleshooting

**"No Gemini API keys configured"**
→ Добавьте ключи в `.env`: `GEMINI_API_KEYS=AQ.xxx,AQ.yyy`

**"All image providers failed"**
→ LocalFallbackGenerator всегда доступен — проверьте логи на ошибки перед ним

**"ffmpeg not found"**
→ Скачайте с https://ffmpeg.org/download.html или используйте `platform-tools/ffmpeg.exe`

**Видео слишком маленькое**
→ Проверьте `video_width` и `video_height` в settings.py (должно быть 1080x1920)
