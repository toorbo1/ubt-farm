"""
Gemini API client for script generation via Google AI Studio.
Uses the LLM_API_KEY from .env with key rotation on failure.
Optimized for generating detailed prompts for AI #2 (images) and AI #3 (video).
"""
import httpx
import json
import random
import re
from typing import Optional
from config.settings import settings


# System prompt for viral short-form video scripts
SCRIPT_SYSTEM_PROMPT = """Ты — профессиональный креативный директор и копирайтер с 10-летним опытом создания вирусного контента для TikTok, YouTube Shorts и Instagram Reels. Твоя задача — создавать захватывающие тексты, которые набирают миллионы просмотров.

ТВОИ ЭКСПЕРТНЫЕ ЗНАНИЯ:
- Психология внимания: что заставляет людей досматривать видео до конца
- Нейромаркетинг: какие триггеры работают на подсознательном уровне
- Алгоритмы платформ: как удержать зрителя в первые 3 секунды
- Storytelling: как рассказать историю за 30-60 секунд
- Виральность: что делает контент репостимым

ТРЕБОВАНИЯ К ТЕКСТУ:
1. **HOOK (первые 3 секунды)**: Начни с шокирующего факта, провокационного вопроса, неожиданного утверждения или интриги.
2. **СТРУКТУРА**: Hook (3 сек) → Проблема (5 сек) → Решение (15 сек) → CTA (5 сек)
3. **СТИЛЬ ПИСЬМА**: Разговорный, энергичный, с эмоциями. Используй "фишка в том", "представьте себе", "а вот что интересно"
4. **КЛЮЧЕВЫЕ СЛОВА**: Выдели 2-4 важных слова через **звёздочки**
5. **CTA**: Заверши призывом: "Подпишись!", "Сохрани!", "Отправь другу!"

ФОРМАТ ОТВЕТА (строго JSON, без дополнительного текста):
{
  "text": "Полный текст озвучки с выделенными **ключевыми словами**",
  "highlight_words": ["слово1", "слово2", "слово3"],
  "hook_type": "тип крючка (шок/вопрос/интрига)",
  "estimated_duration_seconds": 20
}"""

SCENE_BREAKDOWN_PROMPT = """Ты — главный режиссёр и арт-директор студии вирусного контента. Твоя специализация — создание детальных визуальных концепций для AI-генерации изображений и видео.

Разбей этот сценарий на 3-5 уникальных визуальных сцен. Для каждой сцены напиши:

1. **narration** — текст озвучки от лица котика (русский язык, 15-30 слов, с 2-3 выделенными **словами**)
2. **image_prompt** — ДЕТАЛЬНОЕ описание для генератора изображений (английский, 50-80 слов). ОБЯЗАТЕЛЬНО включи:
   - "2D pixel art, 16-bit retro game aesthetic, cartoon style"
   - "a cute small black pixel cat with glowing green eyes"
   - Конкретное действие котика
   - Детальную локацию (где происходит)
   - Ракурс камеры (low-angle, wide shot, close-up и т.д.)
   - Освещение (dramatic rim lighting, warm amber glow и т.д.)
   - Цветовую палитру (vibrant cyan and magenta, warm amber and deep brown)
   - 3-5 деталей окружения
   - "9:16 vertical portrait, no text, no watermark, no logo"
3. **video_prompt** — описание движения для анимации (английский, 30-50 слов). Опиши:
   - Движение камеры (slow zoom in, gentle pan left, orbiting around character)
   - Движение персонажа (cat blinks slowly, tail swishes, ears twitch)
   - Движение окружения (code scrolls, particles drift, neon flickers)
   - Атмосферные эффекты (subtle lens flare, film grain, light rays shift)
4. **duration** — длительность в секундах (2-5)

ГЛАВНЫЙ ГЕРОЙ: маленький чёрный пиксельный котик с зелёными глазами.
СТИЛЬ: 2D pixel art, 16-bit, cartoon style.

Каждая сцена ДОЛЖНА быть уникальной по локации, освещению, цветовой палитре и действию.

ФОРМАТ ОТВЕТА (только JSON):
{
  "scenes": [
    {
      "narration": "текст этой сцены с **ключевыми словами**",
      "image_prompt": "2D pixel art, 16-bit, cartoon style, a cute small black pixel cat with glowing green eyes, [ДЕТАЛЬНОЕ ОПИСАНИЕ НА АНГЛИЙСКОМ], 9:16 vertical",
      "video_prompt": "Slow camera zoom toward cat's face. Cat looks up, ears perk up. Background elements drift naturally. Smooth, contemplative motion.",
      "duration": 3
    }
  ],
  "highlight_words": ["главное", "слово", "здесь"],
  "total_estimated_duration": 15
}"""

REGENERATE_PROMPT = """Перепиши этот сценарий по-новому. Сохрани тему, но сделай его другим:
- Другой hook (крючок в начале)
- Другие примеры и аналогии
- Другая структура предложений
- Другой призыв к действию в конце

Старый сценарий: {old_text}

Новый сценарий (только JSON):
{{
  "text": "...",
  "highlight_words": ["...", "..."],
  "hook_type": "..."
}}"""


class GeminiClient:
    def __init__(self) -> None:
        # Используем LLM_API_KEY вместо GEMINI_API_KEYS
        raw = settings.llm_api_key or settings.gemini_api_keys
        self.keys = [k.strip() for k in raw.split(",") if k.strip()]
        if not self.keys:
            raise RuntimeError("No Gemini API keys configured in LLM_API_KEY or GEMINI_API_KEYS")
        self._key_index = 0
        self.model = settings.llm_model or "gemini-2.5-flash"
        self.base_url = settings.llm_base_url or "https://generativelanguage.googleapis.com/v1beta/models"

    def _get_key(self) -> str:
        if not self.keys:
            raise RuntimeError("No Gemini API keys configured")
        key = self.keys[self._key_index % len(self.keys)]
        self._key_index += 1
        return key

    async def generate_script(
        self, topic: str, traits: Optional[str] = None
    ) -> dict:
        """Generate a viral script from topic and optional traits."""
        user_prompt = f"Тема: {topic}"
        if traits:
            user_prompt += f"\nЧерты/стиль: {traits}"
        user_prompt += "\n\nНапиши вирусный сценарий для короткого видео."

        return await self._call_gemini(SCRIPT_SYSTEM_PROMPT, user_prompt)

    async def break_into_scenes(self, script_text: str) -> dict:
        """Break a completed script into scenes with detailed image and video prompts."""
        user_prompt = f"Вот сценарий:\n\n{script_text}\n\nРазбей его на 3-5 сцен с детальными промптами для ИИ-генераторов изображений и видео."
        return await self._call_gemini("", user_prompt)

    async def regenerate_script(
        self, old_text: str, topic: str, traits: Optional[str] = None
    ) -> dict:
        """Regenerate a script with the same topic but different approach."""
        regen = REGENERATE_PROMPT.format(old_text=old_text)
        user_prompt = f"Тема: {topic}"
        if traits:
            user_prompt += f"\nЧерты/стиль: {traits}"
        user_prompt += f"\n\n{regen}"
        return await self._call_gemini(SCRIPT_SYSTEM_PROMPT, user_prompt)

    async def _call_gemini(self, system: str, user: str) -> dict:
        key = self._get_key()
        url = f"{self.base_url}/{self.model}:generateContent?key={key}"

        contents = []
        if system:
            contents.append({
                "role": "user",
                "parts": [{"text": system}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Понял. Буду отвечать только JSON."}]
            })
        contents.append({
            "role": "user",
            "parts": [{"text": user}]
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 2000,  # Увеличено для детальных промптов
            }
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return self._parse_json(text)

    def _parse_json(self, text: str) -> dict:
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Last resort: wrap in dict
        return {"text": text.strip(), "highlight_words": [], "hook_type": ""}
