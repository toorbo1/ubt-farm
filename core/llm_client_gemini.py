"""
AI #1: LLM клиент для работы с Google Gemini API.
Генерирует тексты, сценарии и детальные промпты для ИИ #2 (изображения) и ИИ #3 (видео).
"""
import httpx
import json
import random
import re
from typing import Optional
from pathlib import Path

from config.settings import settings


# Системный промпт для генерации текстов (короткие видео)
SYSTEM_PROMPT = """Ты — профессиональный креативный директор и копирайтер с 10-летним опытом создания вирусного контента для TikTok, YouTube Shorts и Instagram Reels. Твоя задача — создавать захватывающие тексты, которые набирают миллионы просмотров.

ТВОИ ЭКСПЕРТНЫЕ ЗНАНИЯ:
- Психология внимания: что заставляет людей досматривать видео до конца
- Нейромаркетинг: какие триггеры работают на подсознательном уровне
- Алгоритмы платформ: как удержать зрителя в первые 3 секунды
- Storytelling: как рассказать историю за 30-60 секунд
- Виральность: что делает контент репостимым

ТРЕБОВАНИЯ К ТЕКСТУ:
1. **HOOK (первые 3 секунды)**: Начни с шокирующего факта, провокационного вопроса, неожиданного утверждения или интриги. Примеры:
   - "Вы не поверите, но..."
   - "Это изменит всё..."
   - "99% людей об этом не знают..."
   - "Представьте ситуацию..."

2. **СТРУКТУРА**:
   - Hook (3 секунды) → Проблема (5 секунд) → Решение (15 секунд) → CTA (5 секунд)
   - Общий объём: 40-70 слов для 15-30 секундного видео

3. **СТИЛЬ ПИСЬМА**:
   - Разговорный, как будто рассказываешь другу
   - Энергичный, с эмоциями
   - Без канцеляризмов и сложных конструкций
   - Используй риторику: вопросы, восклицания, паузы
   - Добавляй "живые" выражения: "фишка в том", "представьте себе", "а вот что интересно"

4. **КЛЮЧЕВЫЕ СЛОВА**: Выдели 2-4 важных слова через **звёздочки** — это будут визуальные акценты в видео

5. **CTA (Call To Action)**: Заверши призывом:
   - "Подпишись, чтобы не пропустить!"
   - "Сохрани себе — пригодится!"
   - "Отправь другу, которому это нужно!"
   - "Напиши в комментариях своё мнение!"

ТЕМЫ ДЛЯ КОНТЕНТА:
- Технологии и ИИ: нейросети, гаджеты, цифровые тренды
- Кибербезопасность: VPN, пароли, защита данных, фишинг
- Лайфхаки: продуктивность, экономия, обучение, привычки
- Финансы: инвестиции, экономия, заработок, криптовалюта
- Наука: космос, медицина, психология, биология
- Саморазвитие: мотивация, дисциплина, навыки, книги
- Гейминг: киберспорт, стратегии, секреты игр
- Будущее: роботы, автоматизация, новые профессии

ФОРМАТ ОТВЕТА (строго JSON, без дополнительного текста):
{
  "text": "Полный текст озвучки с выделенными **ключевыми словами**",
  "highlight_words": ["слово1", "слово2", "слово3"],
  "hook_type": "тип крючка (шок/вопрос/интрига)",
  "estimated_duration_seconds": 20
}"""

# Random session ID to force unique outputs across runs
_SESSION_ID = random.randint(100000, 999999)
_RUN_COUNTER = [0]  # mutable counter across calls in same process

# Промпт для генерации сценариев с детальными промптами для ИИ #2 и ИИ #3
SCENE_PROMPT_TEMPLATE = """Ты — главный режиссёр и арт-директор студии вирусного контента. Твоя специализация — создание детальных визуальных концепций для AI-генерации изображений и видео. Ты работаешь в стиле 2D pixel art с главным героем — маленьким чёрным пиксельным котиком с зелёными глазами.

Session ID: {_session_id}
Run number: {_run_num}

ТВОИ ЗАДАЧИ:
1. Создать 3-5 уникальных визуальных сцен для видео
2. Для каждой сцены написать ДЕТАЛЬНЫЙ промпт для AI-генератора изображений (ИИ #2)
3. Для каждой сцены написать промпт для AI-генератора видео (ИИ #3), описывающий движение и анимацию

=== СТРУКТУРА КАЖДОЙ СЦЕНЫ ===

Каждая сцена содержит 4 элемента:
1. **narration** — текст озвучки от лица котика (русский язык)
2. **image_prompt** — детальное описание для генерации изображения (английский язык)
3. **video_prompt** — детальное описание движения для анимации (английский язык)
4. **duration** — длительность сцены в секундах (2-5)

=== ПРАВИЛА ДЛЯ NARRATION (озвучка) ===

- Пиши от первого лица: "я показываю", "мы узнаем", "смотрите что"
- Стиль: дружеская беседа, энергично, с энтузиазмом
- Используй: "вау", "представляете?", "это невероятно!", "фишка в том"
- Выделяй 2-3 слова через **звёздочки** для визуального акцента
- Каждая сцена = одна законченная мысль
- Объём: 15-30 слов на сцену

=== ПРАВИЛА ДЛЯ IMAGE_PROMPT (для ИИ #2 - генерация изображений) ===

ФОРМАТ: Один связный текст на английском, 50-80 слов

ОБЯЗАТЕЛЬНЫЕ ЭЛЕМЕНТЫ (всегда включать):
1. **Стиль**: "2D pixel art, 16-bit retro game aesthetic, cartoon style"
2. **Персонаж**: "a cute small black pixel cat with glowing green eyes"
3. **Действие**: что делает котик (конкретно!)
4. **Локация**: где происходит (детально!)
5. **Композиция**: ракурс камеры, перспектива
6. **Освещение**: источник света, тип освещения
7. **Цветовая палитра**: 2-3 основных цвета
8. **Детали**: 3-5 объектов окружения
9. **Атмосфера**: настроение сцены
10. **Формат**: "9:16 vertical portrait, no text, no watermark, no logo"

ПРИМЕРЫ КАЧЕСТВЕННЫХ IMAGE_PROMPT:

Пример 1 (технологии):
"2D pixel art, 16-bit retro game aesthetic, cartoon style. A cute small black pixel cat with glowing green eyes sitting cross-legged on a floating holographic keyboard, paws actively typing with visible keystroke sparks, surrounded by multiple translucent screens showing code snippets and data streams. Cluttered cyberpunk room with walls covered in sticky notes, empty coffee cups, vintage arcade cabinet in corner. Low-angle hero shot, dramatic rim lighting from monitors casting cyan glow on cat's fur, volumetric fog. Color palette: electric blue, hot pink, deep purple. Foreground details: floating data particles, steam rising from mug. Sharp pixel edges, rich dithering, intricate textures. 9:16 vertical portrait, no text, no watermark, no logo."

Пример 2 (кибербезопасность):
"2D pixel art, 16-bit retro game aesthetic, cartoon style. A cute small black pixel cat with glowing green eyes standing confidently on hind legs, holding oversized golden key like a sword, defensive stance in front of massive steel vault door with digital keypad. Background shows shadowy figures with question marks trying to approach but blocked by glowing shield barrier. Night time urban rooftop setting with neon-lit skyscrapers in distance. Wide establishing shot, spotlight on cat and vault, dramatic contrast. Color palette: metallic silver, warning red, security green. Details: binary code raining in background, padlock icons floating, spark effects where shield meets shadows. Pixel-perfect precision, clean anti-aliased edges. 9:16 vertical portrait, no text, no watermark, no logo."

Пример 3 (уютная атмосфера):
"2D pixel art, 16-bit retro game aesthetic, cartoon style. A cute small black pixel cat with glowing green eyes curled up asleep on warm glowing laptop keyboard, peaceful expression, tiny paw tucked under chin. Cozy attic bedroom with slanted ceiling, string lights hanging above, bookshelf overflowing with colorful spines, potted plants on windowsill, rain visible through window. Tight close-up composition, warm amber table lamp creating soft pool of light, gentle bokeh effect. Color palette: warm amber, soft cream, muted sage green, rusty orange. Atmospheric details: dust motes dancing in light beam, condensation on window glass, wrinkled blanket texture. Intimate mood, hygge aesthetic. Crisp pixel art with smooth gradients. 9:16 vertical portrait, no text, no watermark, no logo."

=== ПРАВИЛА ДЛЯ VIDEO_PROMPT (для ИИ #3 - анимация) ===

ФОРМАТ: Один связный текст на английском, 30-50 слов

ЧТО ОПИСЫВАТЬ:
- Движение камеры: "slow zoom in", "gentle pan left", "orbiting around character"
- Движение персонажа: "cat blinks slowly", "tail swishes rhythmically", "ears twitch", "paws gesture while explaining"
- Движение окружения: "code scrolls on monitors", "particles drift upward", "neon signs flicker", "rain falls in background"
- Атмосферные эффекты: "subtle lens flare", "film grain", "light rays shift", "smoke wisps"
- Настроение движения: "calm and contemplative", "energetic and bouncy", "smooth and cinematic"

ПРИМЕРЫ КАЧЕСТВЕННЫХ VIDEO_PROMPT:

Пример 1: "Slow camera zoom toward cat's face. Cat looks up from keyboard, ears perk up, turns head to viewer with curious expression. Code continues scrolling on background monitors. Floating data particles drift lazily upward. Subtle neon sign flicker outside window. Gentle ambient light pulsing. Smooth, contemplative motion."

Пример 2: "Camera circles around cat in slow arc. Cat gestures dramatically with paw toward vault door, tail swishing for emphasis. Golden key glows brighter when mentioned. Shadowy figures in background retreat slowly. Shield barrier pulses with protective energy. Dynamic, confident movement with clear focal points."

Пример 3: "Static camera with slight handheld shake for realism. Cat breathes gently while sleeping, tiny paw occasionally twitching. Rain streaks down window in steady rhythm. String lights sway almost imperceptibly. Dust motes float in warm light beams. Laptop screen glow subtly pulses. Peaceful, meditative motion."

=== ТРЕБОВАНИЯ К УНИКАЛЬНОСТИ ===

Каждая сцена ДОЛЖНА отличаться по:
- Локации (не повторяй комнаты, улицы, офисы)
- Времени суток (утро/день/вечер/ночь)
- Освещению (мягкое/резкое/неоновое/естественное)
- Цветовой палитре (меняй комбинации)
- Ракурсу камеры (низкий/высокий/крупный план/общий)
- Действию персонажа (сидит/стоит/движется/взаимодействует)
- Настроению (энергичное/спокойное/загадочное/весёлое)

ФОРМАТ ОТВЕТА (только JSON, ничего больше):
{{
  "scenes": [
    {{
      "narration": "Текст озвучки с **акцентами**",
      "image_prompt": "Detailed English description for AI image generator...",
      "video_prompt": "Detailed English motion description for AI video generator...",
      "duration": 3
    }}
  ],
  "highlight_words": ["главное", "слово", "здесь"],
  "total_estimated_duration": 15
}}"""


def get_scene_prompt(topic: Optional[str] = None) -> str:
    """Generate a unique scene prompt with randomized elements."""
    _RUN_COUNTER[0] += 1
    prompt = SCENE_PROMPT_TEMPLATE.format(
        _session_id=_SESSION_ID,
        _run_num=_RUN_COUNTER[0]
    )
    if topic:
        prompt += f"\n\nТема видео: {topic}"
    return prompt


class LLMClient:
    """Клиент для работы с Google Gemini API."""

    def __init__(self) -> None:
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.base_url = settings.llm_base_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def generate_script(self, topic: Optional[str] = None) -> dict:
        """Генерирует короткий текст для видео через Gemini API."""
        if not self.api_key:
            return self._default_script(topic)

        prompt = SYSTEM_PROMPT
        if topic:
            prompt += f"\n\nТема видео: {topic}"

        # Gemini API формат
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 500,
            }
        }

        headers = {
            "Content-Type": "application/json",
        }

        try:
            # Gemini использует URL с моделью в конце
            url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
            resp = await self.client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_response(content)
        except Exception as e:
            print(f"[LLM] Gemini API error: {e}, using default script")
            return self._default_script(topic)

    async def generate_scenes(self, topic: Optional[str] = None) -> dict:
        """Генерирует сценарий с разбивкой по сценам с детальными промптами для ИИ #2 и ИИ #3."""
        if not self.api_key:
            return self._default_scenes(topic)

        prompt = get_scene_prompt(topic)

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.95,
                "maxOutputTokens": 2000,
            }
        }

        headers = {
            "Content-Type": "application/json",
        }

        try:
            url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
            resp = await self.client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            result = self._parse_response(content)

            # Validate structure
            if "scenes" in result and isinstance(result["scenes"], list):
                return result

            # Fallback to combinatorial unique scenes
            return self._default_scenes(topic)
        except Exception as e:
            print(f"[LLM] Gemini API error: {e}, using combinatorial fallback")
            return self._default_scenes(topic)

    def _default_scenes(self, topic: Optional[str] = None) -> dict:
        """Fallback с комбинаторными промптами."""
        default = self._default_script(topic)
        text = default["text"]
        words = text.split()
        chunk_size = max(2, min(5, len(words) // 4))

        chunks = [
            " ".join(words[i:i + chunk_size])
            for i in range(0, len(words), chunk_size)
        ]
        prompts = self._build_scene_prompts(len(chunks), topic)

        scenes = []
        for chunk, image_prompt in zip(chunks, prompts):
            scenes.append({
                "narration": chunk,
                "image_prompt": image_prompt,
                "video_prompt": "Slow camera movement with subtle ambient motion. Cat blinks occasionally, tail sways gently. Background elements drift naturally. Calm, contemplative atmosphere.",
                "duration": max(2, min(4, len(chunk.split()) // 3 + 1)),
            })

        return {
            "scenes": scenes,
            "highlight_words": default.get("highlight_words", ["подпишись"]),
        }

    SCENE_LOCATIONS = [
        "a cluttered hacker den with CRT monitors stacked to the ceiling",
        "a rain-soaked neon alley between towering arcade signs",
        "a cozy attic room with a sloped window full of stars",
        "a floating island built from circuit boards above pixel clouds",
        "a futuristic rooftop garden overlooking a holographic skyline",
        "a bright research laboratory full of bubbling beakers and cables",
        "an abandoned subway station lit by flickering emergency lamps",
        "a sunlit coffee shop with plants and a chalkboard menu",
        "a server room corridor with racks glowing in the dark",
        "a snowy mountain observatory with a giant satellite dish",
        "a retro video rental store with shelves of pixel cassettes",
        "a desert highway at dusk with a lone neon motel sign",
    ]
    SCENE_ACTIONS = [
        "typing furiously on a mechanical keyboard, code reflected in its eyes",
        "leaping between floating platforms of light",
        "curled up asleep on a warm glowing laptop",
        "holding up a tiny lantern that lights the whole scene",
        "staring at a giant holographic screen with a paw raised",
        "pulling a glowing cable out of a wall panel",
        "balancing on a wire above the street, tail out for balance",
        "pointing at a chart floating in mid-air",
        "peeking out from behind a stack of hardware",
        "riding a hoverboard through a stream of data particles",
    ]
    SCENE_LIGHTING = [
        "dramatic rim lighting with deep shadows",
        "soft warm amber glow from a single lamp",
        "cold blue moonlight through a window",
        "flickering neon reflections on wet surfaces",
        "harsh top-down spotlight with volumetric dust",
        "golden hour sunbeams cutting across the room",
    ]
    SCENE_PALETTES = [
        "vibrant cyan and magenta neon palette",
        "warm amber and deep brown palette",
        "electric blue and hot pink palette",
        "muted teal and rust orange palette",
        "purple and lime green high-contrast palette",
        "monochrome green CRT palette with one red accent",
    ]
    SCENE_CAMERAS = [
        "low-angle hero shot",
        "wide establishing shot",
        "tight close-up on the character",
        "over-the-shoulder composition",
        "top-down isometric view",
        "dutch-angle dynamic framing",
    ]
    SCENE_DETAILS = [
        "floating data particles and dust motes",
        "steam rising from a coffee mug",
        "rain streaks and puddle reflections",
        "sparks arcing from exposed wiring",
        "paper notes pinned to every surface",
        "tiny glowing fireflies drifting past",
    ]

    @classmethod
    def _build_scene_prompts(cls, count: int, topic: Optional[str] = None) -> list[str]:
        """Combinatorial fallback prompts — never repeats within one video."""
        def spread(pool: list[str]) -> list[str]:
            out: list[str] = []
            while len(out) < count:
                batch = pool[:]
                random.shuffle(batch)
                out.extend(batch)
            return out[:count]

        locations = spread(cls.SCENE_LOCATIONS)
        actions = spread(cls.SCENE_ACTIONS)
        lightings = spread(cls.SCENE_LIGHTING)
        palettes = spread(cls.SCENE_PALETTES)
        cameras = spread(cls.SCENE_CAMERAS)
        details = spread(cls.SCENE_DETAILS)

        theme = f" The scene hints at the theme of {topic}." if topic else ""
        prompts = []
        for i in range(count):
            prompts.append(
                f"2D pixel art, 16-bit retro game aesthetic, cartoon style. "
                f"A cute small black pixel cat with glowing green eyes, {actions[i]}, "
                f"in {locations[i]}. {cameras[i].capitalize()}, {lightings[i]}, "
                f"{palettes[i]}. Foreground detail: {details[i]}. "
                f"Crisp pixel edges, rich dithering, intricate textures on every surface, "
                f"cinematic depth.{theme} "
                f"Vertical 9:16 portrait composition. No text, no watermark, no logo."
            )
        return prompts

    @staticmethod
    def _default_script(topic: Optional[str] = None) -> dict:
        texts_pool = {
            "vpn и приватность": [
                ("Представьте: вы в кафе, пьёте кофе, а кто-то за соседним столиком "
                 "читает все ваши сообщения. Страшно? А ведь **общественный Wi-Fi** "
                 "работает именно так. VPN шифрует всё, что вы отправляете. "
                 "Никто не увидит ваш трафик. **Защита** — это просто. Подпишись!"),
                ("Знаете, кто больше всех радуется бесплатному Wi-Fi? **Хакеры**. "
                 "Открытая сеть — это как стеклянный дом: всё видно насквозь. "
                 "VPN превращает его в бетонный бункер. Ваши **пароли** под надёжной защитой. "
                 "Сохраните этот совет — пригодится!"),
            ],
            "интернет технологии": [
                ("Вы держите в руках устройство мощнее, чем компьютеры NASA в 1969 году. "
                 "И используете его для котиков. А что, если направить эту **мощь** "
                 "на что-то полезное? Нейросети, big data, облака — **будущее** уже здесь. "
                 "Будьте умнее — подпишитесь!"),
            ],
            "кибербезопасность": [
                ("Самый слабый элемент любой системы — **человек**. "
                 "Хакеры не взламывают компьютеры, они взламывают людей. "
                 "Вам пришло письмо от 'банка'? Не переходите по ссылке. "
                 "Проверяйте **адрес** отправителя. Сохраните этот совет!"),
            ],
        }
        general_pool = [
            "Вы проводите в телефоне 6 часов в день. Это 90 дней в году. "
            "А что, если превратить это время в **суперсилу**? "
            "Учитесь, читайте, развивайтесь. **Время** — единственный ресурс, "
            "который не купишь. Используйте его мудро! Подпишитесь!",
            "Деньги не приносят счастья, но их отсутствие приносит стресс. "
            "**Финансовая грамотность** — это навык, которому не учат в школе. "
            "20% дохода откладывайте сразу. Через 5 лет у вас будет **капитал**. "
            "Подпишитесь на канал — будет много полезного!",
        ]
        if topic and topic.lower() in texts_pool:
            text = random.choice(texts_pool[topic.lower()])
        else:
            text = random.choice(general_pool)
        highlight = re.findall(r"\*\*(.+?)\*\*", text)
        if not highlight:
            highlight = ["подпишись"]
        clean = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        return {"text": clean, "highlight_words": highlight}

    async def generate_hashtags(self, text: str, count: int = 10) -> list[str]:
        """Генерирует хештеги через Gemini API."""
        prompt = (
            f"Напиши {count} хештегов для TikTok/Reels/Shorts "
            f"по теме: {text}. Только хештеги через пробел, без лишнего текста."
        )

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.5,
                "maxOutputTokens": 200,
            }
        }

        headers = {"Content-Type": "application/json"}

        try:
            url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
            resp = await self.client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            return re.findall(r"#\w+", content)
        except Exception as e:
            raise RuntimeError(f"Hashtag generation failed: {e}")

    def _parse_response(self, content: str) -> dict:
        """Парсит JSON из ответа Gemini."""
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: извлекаем текст и слова в **
        highlight = re.findall(r"\*\*(.+?)\*\*", content)
        clean_text = re.sub(r"\*\*.+?\*\*", lambda m: m.group(1), content)
        return {
            "text": clean_text.strip().strip('"'),
            "highlight_words": highlight,
        }

    async def close(self) -> None:
        await self.client.aclose()
