#!/usr/bin/env python3
"""
Telegram Bot for UBT Traffic Farm + VPN Monitor.
Управление через reply-кнопки (панель ввода).

Запуск:
  python -m bot.run_bot --bot 1
  python -m bot.run_bot --bot 2
  python -m bot.run_bot --token TOKEN
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Final

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from bot.handlers import (
    AWAIT_CUSTOM_TEXT,
    AWAIT_TOPIC,
    AWAIT_TRAITS,
    AWAIT_SCRIPT_ACTION,
    start,
    handle_text,
    custom_text_received,
    handle_gemini_topic,
    handle_gemini_traits,
    _handle_pipeline_callback,
    about_ventura_handler,
    about_ventura_back_handler,
    cancel,
    error_handler,
)
from bot.keyboards import topics_kb


async def _gemini_action_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Wrapper to extract text and pass to handle_gemini_action."""
    from bot.handlers import handle_gemini_action
    text = update.message.text.strip() if update.message else ""
    return await handle_gemini_action(update, context, text)


from bot.vpn_handlers import vpn_server_detail

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def build_app(token: str) -> Application:
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))

    # Conversation для генерации сценария через DeepSeek (должен быть ДО общего обработчика)
    async def start_gemini_script(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Entry point for DeepSeek script generation."""
        context.user_data["section"] = "gemini_script"
        await update.message.reply_text(
            "[INFO] Тема для сценария\n\nНапиши тему, например:\n- VPN и приватность\n- Интернет технологии\n- Кибербезопасность",
            parse_mode="Markdown",
            reply_markup=topics_kb()
        )
        return AWAIT_TOPIC

    conv_gemini = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^Создать сценарий$"), start_gemini_script),
        ],
        states={
            AWAIT_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gemini_topic),
            ],
            AWAIT_TRAITS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gemini_traits),
            ],
            AWAIT_SCRIPT_ACTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _gemini_action_wrapper),
            ],
            AWAIT_CUSTOM_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, custom_text_received),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_gemini)

    # Conversation для своего текста
    conv_custom = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✏ Свой текст$"), handle_text)],
        states={
            AWAIT_CUSTOM_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, custom_text_received)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_custom)

    # Главный обработчик текстовых кнопок (после ConversationHandler'ов)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Inline-кнопки: пайплайн
    app.add_handler(CallbackQueryHandler(_handle_pipeline_callback, pattern="^pipe_"))
    # Inline-кнопки (детали VPN сервера)
    app.add_handler(CallbackQueryHandler(vpn_server_detail, pattern="^vpn_server_"))
    # Inline-кнопки "О Ventura"
    app.add_handler(CallbackQueryHandler(about_ventura_handler, pattern="^about_ventura$"))
    app.add_handler(CallbackQueryHandler(about_ventura_back_handler, pattern="^about_back$"))

    app.add_error_handler(error_handler)
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="UBT Farm + VPN Bot")
    parser.add_argument("--token", help="Telegram Bot API token")
    parser.add_argument(
        "--bot", type=int, choices=[1, 2], default=1,
        help="Bot 1 (основной) или Bot 2 (новый)",
    )
    args = parser.parse_args()

    token = args.token
    if not token:
        if args.bot == 2:
            token = getattr(settings, "telegram_bot_token_2", None)
        if not token:
            token = getattr(settings, "telegram_bot_token", None)

    if not token:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("TELEGRAM_BOT_TOKEN"):
                    token = line.split("=", 1)[1].strip()
                    break

    if not token:
        print("Токен бота не найден. Укажи --token или --bot 1/2")
        sys.exit(1)

    bot_label = "Bot 1" if args.bot == 1 else "Bot 2"
    app = build_app(token)
    logger.info(f"UBT Farm + VPN Monitor {bot_label} started")
    print(f"Бот запущен. Напиши /start в Telegram.")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
