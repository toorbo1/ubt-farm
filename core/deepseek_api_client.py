"""
DeepSeek API client - uses official DeepSeek API (free tier, no auth required for basic usage).
"""
import httpx
import json
import re
from typing import Optional


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


class DeepSeekAPIClient:
    def __init__(self) -> None:
        # DeepSeek official API endpoint (free tier available)
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"

    async def generate_script(
        self, topic: str, traits: Optional[str] = None
    ) -> dict:
        """Generate a viral script from topic and optional traits."""
        user_prompt = f"Тема: {topic}"
        if traits:
            user_prompt += f"\nЧерты/стиль: {traits}"
        user_prompt += "\n\nНапиши вирусный сценарий для короткого видео."

        return await self._call_api(SCRIPT_SYSTEM_PROMPT, user_prompt)

    async def break_into_scenes(self, script_text: str) -> dict:
        """Break a completed script into scenes with detailed prompts."""
        system = """Ты — главный режиссёр и арт-директор студии вирусного контента. Разбей этот сценарий на 3-5 уникальных визуальных сцен.

ФОРМАТ ОТВЕТА (только JSON):
{
  "scenes": [
    {
      "narration": "текст этой сцены с **ключевыми словами**",
      "image_prompt": "2D pixel art, 16-bit, cartoon style, a cute small black pixel cat with glowing green eyes, [ДЕТАЛЬНОЕ ОПИСАНИЕ НА АНГЛИЙСКОМ], 9:16 vertical",
      "video_prompt": "Slow camera zoom toward cat's face. Cat looks up, ears perk up. Background elements drift naturally.",
      "duration": 3
    }
  ],
  "highlight_words": ["главное", "слово", "здесь"],
  "total_estimated_duration": 15
}"""
        user_prompt = f"Вот сценарий:\n\n{script_text}\n\nРазбей его на 3-5 сцен с детальными промптами для ИИ-генераторов изображений и видео."
        return await self._call_api(system, user_prompt)

    async def regenerate_script(
        self, old_text: str, topic: str, traits: Optional[str] = None
    ) -> dict:
        """Regenerate a script with the same topic but different approach."""
        regen_prompt = f"""Перепиши этот сценарий по-новому. Сохрани тему, но сделай его другим:
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
        user_prompt = f"Тема: {topic}"
        if traits:
            user_prompt += f"\nЧерты/стиль: {traits}"
        user_prompt += f"\n\n{regen_prompt}"
        return await self._call_api(SCRIPT_SYSTEM_PROMPT, user_prompt)

    async def _call_api(self, system: str, user: str) -> dict:
        """Call DeepSeek API directly."""
        print("[INFO] Отправляю запрос в DeepSeek API...")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": 0.8,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(self.api_url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            text = data["choices"][0]["message"]["content"]
            print("[OK] DeepSeek ответил успешно")
            return self._parse_json(text)

        except Exception as e:
            print(f"[ERROR] Ошибка DeepSeek API: {e}")
            # Fallback to Pollinations
            print("[INFO] Пробую Pollinations.ai...")
            return await self._fallback_pollinations(system, user)

    async def _fallback_pollinations(self, system: str, user: str) -> dict:
        """Fallback to Pollinations.ai if DeepSeek fails."""
        full_prompt = f"{system}\n\n{user}" if system else user

        url = "https://text.pollinations.ai/"

        payload = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that responds in JSON format only."},
                {"role": "user", "content": full_prompt}
            ],
            "jsonMode": True,
            "temperature": 0.8,
            "model": "openai"
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            text = resp.text

        print("[OK] Pollinations ответил успешно")
        return self._parse_json(text)

    def _parse_json(self, text: str) -> dict:
        """Parse JSON from text response."""
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
