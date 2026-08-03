import httpx
import json
import random
import re
from typing import Optional

from config.settings import settings


SYSTEM_PROMPT = """Ты — креативный копирайтер для Shorts/Reels.
Напиши короткий, цепляющий текст (30–50 слов) на русском языке для видео.

Темы: полезные факты, лайфхаки, технологии, кибербезопасность, VPN, интернет.

Правила:
1. Первые 3 слова — hook (крючок, интрига).
2. Простой разговорный язык.
3. Заканчивай призывом: "Подпишись, чтобы не пропустить" или похожим.
4. Выдели 2-3 ключевых слова (оберни их в **звёздочки**).

Формат ответа (только JSON, без лишнего текста):
{"text": "...", "highlight_words": ["...", "..."]}"""

# Random session ID to force unique outputs across runs
_SESSION_ID = random.randint(100000, 999999)
_RUN_COUNTER = [0]  # mutable counter across calls in same process

SCENE_PROMPT_TEMPLATE = """Ты — креативный сценарист для коротких вирусных видео (Shorts/Reels).
Напиши сценарий из 3-5 сцен на русском языке. КАЖДЫЙ РАЗ ПРИДУМЫВАЙ АБСОЛЮТНО НОВЫЙ И УНИКАЛЬНЫЙ СЦЕНАРИЙ, НЕ ПОХОЖИЙ НА ПРЕДЫДУЩИЕ.

Session ID: {_session_id}
Run number: {_run_num}

Темы: полезные факты, лайфхаки, технологии, кибербезопасность, VPN, интернет, здоровье, финансы, космос, наука, природа, путешествия, еда, мода, музыка, кино, игры, спорт, психология, отношения, карьера, бизнес, образование, искусство, история, будущее, роботы, ИИ, виртуальная реальность, криптовалюты, экология, медицина, архитектура, дизайн, фотография, литература, театр, танцы, кулинария, фитнес, йога, медитация, саморазвитие, мотивация, успех, счастье, любовь, дружба, семья, дети, воспитание, школа, университет, работа, зарплата, пенсия, кредит, ипотека, инвестиции, savings, budget, economy, market, stock, crypto, blockchain, AI, ML, DL, NLP, CV, robotics, automation, IoT, smart home, wearable, gadget, app, software, hardware, startup, business, marketing, sales, management, leadership, team, project, product, service, customer, user, experience, interface, design, code, test, deploy, monitor, scale, optimize, secure, protect, privacy, data, info, knowledge, wisdom, learning, teaching, mentoring, coaching, consulting, advising, helping, supporting, caring, sharing, connecting, communicating, collaborating, cooperating, coordinating, organizing, planning, executing, delivering, achieving, succeeding, winning, losing, failing, trying, learning, growing, improving, evolving, adapting, changing, transforming, innovating, creating, building, making, doing, acting, performing, presenting, speaking, writing, reading, listening, understanding, knowing, thinking, feeling, sensing, perceiving, experiencing, living, being, existing, becoming, realizing, awakening, enlightening, inspiring, motivating, empowering, enabling, facilitating, guiding, leading, following, supporting, serving, contributing, giving, receiving, exchanging, trading, buying, selling, renting, lending, borrowing, saving, spending, investing, earning, spending, wasting, losing, finding, discovering, exploring, experimenting, testing, trying, attempting, succeeding, failing, learning, growing, evolving, transforming, transcending, ascending, descending, expanding, contracting, flowing, stopping, starting, pausing, resting, working, playing, sleeping, dreaming, imagining, visualizing, manifesting, attracting, repelling, creating, destroying, preserving, protecting, defending, attacking, competing, cooperating, collaborating, negotiating, compromising, resolving, solving, fixing, healing, curing, treating, preventing, avoiding, escaping, hiding, seeking, searching, finding, losing, winning, succeeding, failing, trying, learning, growing, evolving, transforming, transcending.

ПРАВИЛА ДЛЯ narration (озвучка):
- Главный герой и рассказчик — **маленький чёрный пиксельный котик с зелёными глазами**
- Он объясняет тему зрителю, показывает примеры, задаёт вопросы
- Первые слова — hook, интрига, шок, неожиданный факт или вопрос
- Простой разговорный язык, как будто котик другу рассказывает
- Закончи призывом: подписаться, сохранить, поставить лайк, поделиться
- Выдели 2-3 ключевых слова **звёздочками**
- Каждая сцена — законченная мысль с действиями котика
- Используй разные риторические приёмы: вопросы, восклицания, сравнения, метафоры, аналогии
- Меняй структуру предложений: короткие, длинные, сложные, простые
- Добавляй эмоциональные реакции: удивление, радость, страх, любопытство, восторг
- Используй разные стили повествования: от первого лица, от третьего, диалог, монолог
- Включай разные типы контента: факты, истории, советы, предупреждения, прогнозы
- КАЖДЫЙ СЦЕНАРИЙ ДОЛЖЕН БЫТЬ УНИКАЛЬНЫМ И НЕ ПОВТОРЯТЬ ПРЕДЫДУЩИЕ

ПРАВИЛА ДЛЯ image_prompt (на английском, МАКСИМАЛЬНО ПОДРОБНО):
- ОБЯЗАТЕЛЬНЫЕ УСЛОВИЯ (ВСЕГДА ВКЛЮЧАТЬ):
  * "2D pixel art" — обязательно указать 2D формат
  * "pixel art" или "16-bit" или "8-bit" — обязательно пиксельная графика
  * "cartoon style" или "cartoonish" — обязательно мультяшный стиль
  * "a cute small black pixel cat with glowing green eyes" — главный персонаж
- Жанр: 2D pixel art, 16-bit retro game aesthetic, colorful pixel graphics, cartoon style
- ПОДРОБНОЕ ОПИСАНИЕ КАЖДОЙ СЦЕНЫ:
  * Сюжет: где котик, что делает (сидит на клавиатуре/прыгает/показывает лапкой/печатает/спит/удивляется/танцует/поёт/рисует/готовит/играет/читает/пишет/программирует/чинит/строит/летает/плывёт/бежит/ползёт/катится/крутится/падает/встаёт/сидит/стоит/лежит)
  * Фон: детальное окружение в пикселях (комната/улица/офис/кафе/крыша/библиотека/лес/гора/пляж/пустыня/город/деревня/космос/подводный мир/замок/дворец/пещера/остров/мост/башня/лабиринт/арена/стадион/театр/кинотеатр/музей/галерея/школа/университет/больница/магазин/рынок/порт/аэропорт/вокзал/метро/автобус/поезд/самолёт/корабль/подлодка/ракета/спутник/станция/база/лагерь/дом/квартира/чердак/подвал/гараж/мастерская/лаборатория/студия/офис/кабинет/класс/аудитория/зал/комната/кухня/ванная/спальня/гостиная/прихожая/коридор/лестница/лифт/балкон/терраса/сад/огород/парк/сквер/площадь/улица/дорога/тропа/мост/тоннель/переход/перекрёсток/светофор/знак/указатель/вывеска/реклама/плакат/баннер/щит/экран/монитор/телевизор/проектор/камера/микрофон/динамик/наушник/колонка/усилитель/пульт/джойстик/клавиатура/мышь/тачпад/сенсор/датчик/сканер/принтер/сканер/копир/факс/телефон/смартфон/планшет/ноутбук/компьютер/сервер/роутер/модем/свитч/хаб/патч-панель/кабель/провод/антенна/спутниковая тарелка/солнечная панель/ветрогенератор/генератор/батарея/аккумулятор/зарядка/розетка/выключатель/лампа/светильник/фонарь/прожектор/неон/LED/OLED/LCD/CRT/plasma/display/screen/monitor/projector/camera/microphone/speaker/headphone/earphone/amplifier/mixer/console/controller/keyboard/mouse/touchpad/sensor/scanner/printer/copier/fax/phone/smartphone/tablet/laptop/computer/server/router/modem/switch/hub/patch-panel/cable/wire/antenna/satellite dish/solar panel/wind turbine/generator/battery/accumulator/charger/socket/switch/lamp/light/flashlight/spotlight/neon)
  * Цвета: яркие контрастные, у каждой сцены своя цветовая палитра (cyan/magenta/yellow/green/blue/purple/orange/red/pink/brown/black/white/gray/silver/gold/copper/bronze/neon/pastel/muted/vibrant/bright/dark/light/warm/cool/hot/cold)
  * Детали: предметы вокруг (мониторы/книги/растения/чашки/провода/окна/звёзды/неон/еда/игрушки/инструменты/гаджеты/устройства/машины/роботы/дроны/транспорт/мебель/одежда/обувь/украшения/аксессуары/продукты/напитки/посуда/техника/оборудование/материалы/ресурсы/энергия/свет/тень/отражение/блик/блеск/дым/пар/огонь/вода/воздух/земля/камень/дерево/металл/пластик/стекло/ткань/бумага/кожа/резина/керамика/бетон/асфальт/грунт/песок/пыль/грязь/ржавчина/коррозия/трещины/сколы/царапины/потёртости/пятна/разводы/полосы/точки/линии/круги/квадраты/треугольники/овалы/спирали/волны/зигзаги/ромбы/кресты/звёзды/сердца/стрелы/молнии/облака/дождь/снег/град/туман/роса/иней/лёд/пар/дым/огонь/пламя/искра/вспышка/свет/тень/полутень/контраст/гармония/баланс/симметрия/асимметрия/ритм/повтор/вариация/gradation/transition/transformation/metamorphosis/evolution/revolution/rebellion/uprising/protest/strike/riot/war/peace/love/hate/friendship/enmity/alliance/rivalry/competition/cooperation/collaboration/partnership/friendship/relationship/connection/bond/link/tie/chain/network/web/grid/matrix/lattice/framework/structure/system/organization/institution/corporation/company/business/enterprise/venture/startup/project/initiative/campaign/movement/crusade/mission/quest/journey/adventure/expedition/voyage/trip/tour/visit/excursion/pilgrimage/trek/hike/climb/swim/dive/flight/ride/drive/walk/run/jump/leap/hop/skip/dance/sing/play/work/rest/sleep/eat/drink/read/write/think/feel/sense/perceive/experience/live/love/laugh/cry/smile/frown/scowl/glare/stare/gaze/watch/look/see/hear/listen/smell/taste/touch/hold/carry/lift/pull/push/throw/catch/grab/release/let/go/stop/start/begin/end/finish/complete/accomplish/achieve/succeed/win/lose/fail/try/attempt/effort/struggle/fight/battle/conflict/dispute/argument/debate/discussion/conversation/dialogue/monologue/speech/talk/chat/gossip/rumor/news/report/story/tale/legend/myth/fable/parable/allegory/metaphor/simile/analogy/comparison/contrast/distinction/difference/similarity/likeness/resemblance/identity/equality/equivalence/parity/balance/proportion/ratio/percentage/fraction/portion/share/cut/division/separation/isolation/loneliness/solitude/privacy/secrecy/mystery/puzzle/riddle/enigma/paradox/contradiction/absurdity/nonsense/gibberish/jargon/slang/dialect/accent/pronunciation/articulation/enunciation/diction/elocution/rhetoric/oratory/speaking/presenting/performing/acting/playing/singing/dancing/painting/drawing/sculpting/carving/weaving/knitting/sewing/stitching/embroidering/quilting/crocheting/knotting/braiding/twisting/spinning/weaving/knitting/sewing/stitching/embroidering/quilting/crocheting/knotting/braiding/twisting/spinning)
- Формат: pixel art, game art style, cartoon style, 9:16 vertical portrait
- КАЖДАЯ СЦЕНА должна быть УНИКАЛЬНОЙ и отличаться от других по: локации, действию, цветовой палитре, композиции, освещению, настроению
- НЕ ПОВТОРЯЙ одни и те же описания — используй разные ракурсы, углы, перспективы
- ВАРИРУЙ время суток: утро/день/вечер/ночь/рассвет/закат/полночь/полдень
- ВАРИРУЙ погоду: солнечно/пасмурно/дождь/снег/туман/ветрено/штиль/гроза/радуга
- ВАРИРУЙ настроение: весёлое/грустное/тревожное/спокойное/энергичное/меланхоличное/романтичное/драматичное/комичное/трагичное/героическое/эпическое/лирическое/философское/научное/фантастическое/мистическое/магическое/технологичное/ретро/футуристичное/винтажное/современное/классическое/авангардное/минималистичное/максималистичное

Примеры разных сцен (ВСЕГДА ИСПОЛЬЗУЙ РАЗНЫЕ):
1. "2D pixel art, 16-bit retro game style, cartoon style, a small black pixel cat with glowing green eyes sitting on a giant keyboard, paws typing rapidly, pixel sparks flying from keys, dark room with neon cyan glow from monitors, pixel shelves with retro game cartridges, 9:16 vertical pixel art, low angle shot, dramatic rim lighting, vibrant cyan and magenta palette"
2. "2D pixel art, cute black pixel cat standing on two legs pointing a paw at a giant pixel lock icon, night city background with pixel stars and neon signs, cyberpunk aesthetic, glowing purple and pink colors, cat's eyes reflecting the neon, 9:16 vertical, wide establishing shot, flickering neon reflections, electric blue and hot pink palette"
3. "2D pixel art, black pixel cat sleeping curled up on a glowing laptop, warm amber pixel light, cozy room with pixel plants and bookshelves, soft pixel shadows, comfortable atmosphere, pastel colors, 9:16 vertical, tight close-up, soft warm amber glow, muted teal and rust orange palette"
4. "2D pixel art, black pixel cat riding a hoverboard through a stream of data particles, floating circuit board platforms above pixel clouds, futuristic skyline in background, golden hour sunbeams, lime green and purple high-contrast palette, dynamic dutch-angle framing, 9:16 vertical"
5. "2D pixel art, black pixel cat balancing on a wire above neon-lit street, tail out for balance, rain streaks and puddle reflections below, cold blue moonlight through clouds, monochrome green CRT palette with one red accent, top-down isometric view, 9:16 vertical"

Формат ответа (только JSON, без лишнего текста):
{{
  "scenes": [
    {{
      "narration": "текст озвучки от лица котика с **ключевыми словами**",
      "image_prompt": "2D pixel art, 16-bit, cartoon style, black pixel cat with green eyes, [УНИКАЛЬНОЕ ДЕТАЛЬНОЕ ОПИСАНИЕ СЦЕНЫ], 9:16 vertical",
      "duration": 3
    }}
  ],
  "highlight_words": ["слово1", "слово2"]
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
    def __init__(self) -> None:
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.base_url = settings.llm_base_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def generate_script(self, topic: Optional[str] = None) -> dict:
        if not self.api_key:
            return self._default_script(topic)

        prompt = SYSTEM_PROMPT
        if topic:
            prompt += f"\n\nТема видео: {topic}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Ты — полезный ассистент."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.8,
            "max_tokens": 500,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return self._parse_response(content)
        except Exception as e:
            print(f"[LLM] API error: {e}, using default script")
            return self._default_script(topic)

    async def generate_scenes(self, topic: Optional[str] = None) -> dict:
        """Генерирует сценарий с разбивкой по сценам (для AI #2 + AI #3)."""
        if not self.api_key:
            return self._default_scenes(topic)

        prompt = get_scene_prompt(topic)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Ты — полезный ассистент."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.95,
            "max_tokens": 1200,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            result = self._parse_response(content)
            # Validate structure
            if "scenes" in result and isinstance(result["scenes"], list):
                return result
            # Fallback to combinatorial unique scenes
            return self._default_scenes(topic)
        except Exception as e:
            print(f"[LLM] API error: {e}, using combinatorial fallback")
            return self._default_scenes(topic)

    def _default_scenes(self, topic: Optional[str] = None) -> dict:
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
    def _build_scene_prompts(
        cls, count: int, topic: Optional[str] = None
    ) -> list[str]:
        """Combinatorial fallback prompts — never repeats within one video."""
        def spread(pool: list[str]) -> list[str]:
            # Shuffle then cycle: exhausts the pool before any value repeats
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
                ("Вы когда-нибудь задумывались, почему VPN так популярен? "
                 "Потому что ваш **IP-адрес** — это ваш домашний адрес в интернете. "
                 "Хотите, чтобы каждый знал, где вы живёте? **Приватность** — ваш выбор. "
                 "Подпишитесь, чтобы узнавать больше о безопасности!"),
                ("Это выглядит как магия, но это просто **технология**. "
                 "VPN создаёт зашифрованный туннель между вами и интернетом. "
                 "Ни провайдер, ни хакеры, ни спецслужбы не увидят ваши данные. "
                 "**Анонимность** в сети доступна каждому. Попробуйте!"),
            ],
            "интернет технологии": [
                ("Вы держите в руках устройство мощнее, чем компьютеры NASA в 1969 году. "
                 "И используете его для котиков. А что, если направить эту **мощь** "
                 "на что-то полезное? Нейросети, big data, облака — **будущее** уже здесь. "
                 "Будьте умнее — подпишитесь!"),
                ("Знаете, сколько данных генерирует человечество за минуту? "
                 "500 часов видео на YouTube, 50 миллионов сообщений. "
                 "И всё это хранится в **облаке** — огромных дата-центрах по всему миру. "
                 "**Технологии** не перестают удивлять. Подпишись, чтобы быть в курсе!"),
                ("Искусственный интеллект научился делать видео по тексту. "
                 "Вы пишете 'кот в космосе' — и нейросеть рисует это за секунду. "
                 "**AI** меняет правила игры. Через 5 лет половина контента будет создана "
                 "искусственным интеллектом. **Не отставайте** от прогресса!"),
                ("Квантовые компьютеры — это не научная фантастика. Google уже заявил "
                 "о **квантовом превосходстве**. Задача, которая заняла бы 10.000 лет "
                 "на обычном ПК, решается за минуты. **Наука** движется быстрее, чем мы "
                 "думаем. Подпишитесь, чтобы не пропустить!"),
            ],
            "кибербезопасность": [
                ("Самый слабый элемент любой системы — **человек**. "
                 "Хакеры не взламывают компьютеры, они взламывают людей. "
                 "Вам пришло письмо от 'банка'? Не переходите по ссылке. "
                 "Проверяйте **адрес** отправителя. Сохраните этот совет!"),
                ("Ваш пароль — это как зубная щётка: меняйте каждые 3 месяца "
                 "и ни с кем не делитесь. 123456 — это не пароль, это приглашение. "
                 "Используйте **менеджер паролей** и двухфакторную аутентификацию. "
                 "**Безопасность** начинается с вас. Подпишись!"),
                ("Представьте, что кто-то следит за вами через веб-камеру. "
                 "Это не паранойя — это **реальность**. Заклейте камеру на ноутбуке, "
                 "если она не нужна. Отключайте микрофон, когда не используете. "
                 "**Приватность** — в ваших руках!"),
                ("Бесплатные приложения зарабатывают на ваших данных. "
                 "Каждое ваше действие, каждый клик — это **товар**. "
                 "Рекламодатели платят за ваше внимание. Читайте разрешения перед "
                 "установкой. **Думайте**, прежде чем нажать 'Разрешить'!"),
            ],
            "лайфхаки": [
                ("Хотите запоминать в 2 раза больше? Используйте **мнемотехнику**. "
                 "Связывайте новую информацию с образами. Мозг любит картинки, "
                 "а не сухие факты. **Память** можно тренировать как мышцу. "
                 "Попробуйте сегодня вечером!"),
                ("Самый простой способ сэкономить — правило 24 часов. "
                 "Хотите купить что-то дорогое? Подождите день. "
                 "70% импульсивных покупок отменяются после **паузы**. "
                 "**Деньги** любят счёт. Сохраните себе этот лайфхак!"),
                ("Просыпаетесь уставшим? Проблема не в количестве сна, "
                 "а в его **фазе**. Просыпайтесь в конце цикла — "
                 "через 90 минут после засыпания. Приложения для отслеживания сна "
                 "помогут найти идеальное **время**. Подпишись!"),
                ("Гениальная идея может прийти в любой момент. Носите с собой "
                 "блокнот или используйте заметки в телефоне. **Идеи** улетучиваются "
                 "за 30 секунд. Записывайте всё. **Творчество** — это привычка!"),
            ],
            "гейминг": [
                ("Хотите играть лучше? Забудьте про дорогую периферию. "
                 "Профессиональные киберспортсмены тренируют **рефлексы** "
                 "специальными упражнениями. Aim lab, реакция на свет — "
                 "это работает лучше любого нового скина. **Скилл** решает!"),
                ("Почему в онлайн-шутерах вас убивают из-за угла? "
                 "Дело не в реакции, а в **позиционировании**. "
                 "Держитесь ближе к укрытиям, контролируйте высоту. "
                 "80% успеха — это правильная позиция. **Стратегия** побеждает!"),
                ("Знаете, сколько зарабатывают профессиональные геймеры? "
                 "Топ-игроки в Dota 2 зарабатывают миллионы долларов. "
                 "**Киберспорт** — это не игрушки, это индустрия миллиард. "
                 "Может, ваш **талант** тоже стоит денег?"),
                ("Пинг 200ms против 20ms — это разница между победой и поражением. "
                 "VPN может **снизить** задержку, выбрав маршрут до сервера. "
                 "Попробуйте разные протоколы и сервера. **Скорость** соединения "
                 "решает исход матча. Подпишись на полезные советы!"),
            ],
        }
        general_pool = [
            "Вы проводите в телефоне 6 часов в день. Это 90 дней в году. "
            "А что, если превратить это время в **суперсилу**? "
            "Учитесь, читайте, развивайтесь. **Время** — единственный ресурс, "
            "который не купишь. Используйте его мудро! Подпишитесь!",
            "Секрет успешных людей прост: они делают то, что другие откладывают. "
            "Каждый день — один маленький шаг к **цели**. "
            "Через год вы будете на 365 шагов ближе. **Дисциплина** важнее мотивации. "
            "Начните сегодня. Сохраните этот пост — вернитесь к нему завтра!",
            "Деньги не приносят счастья, но их отсутствие приносит стресс. "
            "**Финансовая грамотность** — это навык, которому не учат в школе. "
            "20% дохода откладывайте сразу. Через 5 лет у вас будет **капитал**. "
            "Подпишитесь на канал — будет много полезного!",
            "А вы знали, что чтение книг по 15 минут в день расширяет словарный запас "
            "на 1000 слов в год? **Книги** — это тренажёр для мозга. "
            "Хотите быть умнее 90% людей? Читайте каждый день. **Развитие** — это привычка. "
            "Поставьте лайк, если любите читать!",
            "Стресс убивает клетки мозга. Буквально. **Медитация** всего по 5 минут "
            "в день восстанавливает нервную систему. Это не эзотерика — это **наука**. "
            "Попробуйте прямо сейчас: глубокий вдох... выдох. Чувствуете? "
            "Подпишитесь — будет ещё полезнее!",
        ]
        if topic and topic.lower() in texts_pool:
            text = random.choice(texts_pool[topic.lower()])
        else:
            text = random.choice(general_pool)
        highlight = []
        for w in re.findall(r"\*\*(.+?)\*\*", text):
            highlight.append(w)
        if not highlight:
            highlight = ["подпишись"]
        clean = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        return {"text": clean, "highlight_words": highlight}

    async def generate_hashtags(self, text: str, count: int = 10) -> list[str]:
        prompt = (
            f"Напиши {count} хештегов для TikTok/Reels/Shorts "
            f"по теме: {text}. Только хештеги через пробел, без лишнего текста."
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.5,
            "max_tokens": 200,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return re.findall(r"#\w+", content)
        except Exception as e:
            raise RuntimeError(f"Hashtag generation failed: {e}")

    def _parse_response(self, content: str) -> dict:
        # Пробуем распарсить JSON из ответа
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
