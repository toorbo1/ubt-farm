from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton


def main_kb() -> ReplyKeyboardMarkup:
    kb = [
        ["✨ Создать сценарий", "🎬 Создать видео"],
        [" Пакет видео", "📤 Загрузить"],
        ["📁 Список видео", "📊 Статус"],
        ["⚙ Настройки AI"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)




def gemini_script_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для режима генерации сценария через Gemini."""
    kb = [
        ["🔄 Переделать", "✏️ Свой текст"],
        ["▶️ Перейти к картинкам", "❌ Отмена"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def farm_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для раздела фермы видео."""
    kb = [
        ["✨ Создать сценарий", "🎬 Создать видео"],
        ["📦 Пакет видео", "📤 Загрузить"],
        ["🔙 В главное меню"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def vpn_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для VPN раздела."""
    kb = [
        ["🔍 Проверить VPN", "📊 Статус VPN"],
        ["🔙 В главное меню"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def ai_models_kb() -> ReplyKeyboardMarkup:
    kb = [
        ["🧠 Сценарий (LLM)", "🖼 Картинки (Image)"],
        ["🎥 Видео (Video)", "⚙ Локальные настройки"],
        ["🔙 В ферму"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def video_provider_kb(providers: list[tuple[str, bool, str]]) -> ReplyKeyboardMarkup:
    rows: list[list[str]] = []
    row: list[str] = []
    for label, usable, _ in providers:
        row.append(f"{'✅' if usable else '🚫'} {label}")
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(["♻ Авто (цепочка)"])
    rows.append(["🔙 Назад"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def topics_kb() -> ReplyKeyboardMarkup:
    kb = [
        ["VPN и приватность", "Интернет технологии"],
        ["Кибербезопасность", "Лайфхаки"],
        ["Гейминг", "✏ Свой текст"],
        ["🔙 Назад"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def batch_kb() -> ReplyKeyboardMarkup:
    kb = [
        ["3 видео", "5 видео", "10 видео"],
        ["🔙 Назад"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def platform_kb() -> ReplyKeyboardMarkup:
    kb = [
        ["TikTok", "YouTube", "Instagram"],
        ["🔙 Назад"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def done_kb() -> ReplyKeyboardMarkup:
    kb = [
        [" Загрузить", "🎬 Ещё видео"],
        ["🔙 В главное меню"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)




def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def vpn_servers_inline(servers: list[dict]) -> InlineKeyboardMarkup:
    kb = []
    for s in servers[:15]:
        name = s.get("server_name", s.get("host", "?"))
        status_icon = "\U0001F7E2" if s.get("status") == "online" else "\U0001F534"
        kb.append([
            InlineKeyboardButton(
                f"{status_icon} {name}",
                callback_data=f"vpn_server_{s['host']}_{s['port']}"
            )
        ])
    return InlineKeyboardMarkup(kb)
