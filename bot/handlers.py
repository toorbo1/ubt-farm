import asyncio
import os
import re
import secrets
import shutil
from pathlib import Path
from typing import Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config.settings import settings
from core.video_ai import available_video_providers
from video_engine.builder import VideoBuilder
from uploader.tiktok import TikTokUploader
from uploader.youtube import YouTubeUploader
from uploader.instagram import InstagramUploader
from .keyboards import (
    main_kb,
    farm_kb,
    topics_kb,
    batch_kb,
    platform_kb,
    done_kb,
    vpn_kb,
    remove_kb,
    vpn_servers_inline,
    ai_models_kb,
    video_provider_kb,
    gemini_script_kb,
)
from .vpn_handlers import vpn_fetch_data
from core.gemini_client import GeminiClient

# Состояния для интерактивной генерации сценариев через Gemini
(
    AWAIT_CUSTOM_TEXT,
    AWAIT_VPN_SERVER,
    AWAIT_AFTER_TEXT,
    AWAIT_AFTER_IMAGES,
    AWAIT_TOPIC,
    AWAIT_TRAITS,
    AWAIT_SCRIPT_ACTION,
) = range(7)

ALLOWED_USERS = set()

def _esc(text: str) -> str:
    """Escape Markdown special chars for parse_mode=Markdown."""
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!])", r"\\\1", text)

# ─── Состояния навигации ───
S_MAIN = "main"
S_FARM = "farm"
S_VPN = "vpn"
S_MODELS = "models"

# Режимы сборки. "step" спрашивает подтверждение после сценария и после
# картинок, "auto" гонит весь пайплайн одним заходом.
MODE_STEP = "step"
MODE_AUTO = "auto"


def _mode(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("pipeline_mode", MODE_STEP)


def _builder(context: ContextTypes.DEFAULT_TYPE) -> VideoBuilder:
    """VideoBuilder с провайдером, выбранным в меню моделей."""
    return VideoBuilder(video_provider=context.user_data.get("video_provider"))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ALLOWED_USERS.add(user.id)
    context.user_data["section"] = S_MAIN
    await update.message.reply_text(
        f"🚀 *Добро пожаловать!*\n\n"
        f"Привет, {user.first_name}!\n"
        f"Это бот для создания вирусных видео с помощью ИИ.\n\n"
        f"✨ *Создать сценарий* — Gemini AI напишет текст\n"
        f"🎬 *Создать видео* — полный пайплайн генерации\n"
        f"📦 *Пакет видео* — создать несколько роликов сразу\n"
        f"\n"
        f"Просто нажимай кнопки внизу ⬇",
        parse_mode="Markdown",
        reply_markup=main_kb(),
    )


async def custom_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик получения своего текста от пользователя."""
    text = update.message.text.strip()
    context.user_data["gemini_script_text"] = text
    context.user_data["section"] = S_FARM

    await update.message.reply_text(
        f"✅ Текст сохранен!\n\n{text[:200]}...\n\n"
        f"Теперь можно:\n"
        f"- Нажать '✨ Создать сценарий' для редактирования\n"
        f"- Или перейти к созданию видео",
        reply_markup=farm_kb()
    )
    return ConversationHandler.END


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    section = context.user_data.get("section", S_MAIN)

    # ─── Глобальные кнопки ───
    if text == "🔙 В главное меню":
        context.user_data["section"] = S_MAIN
        context.user_data.pop("gemini_topic", None)
        context.user_data.pop("gemini_traits", None)
        context.user_data.pop("gemini_script", None)
        context.user_data.pop("gemini_script_text", None)
        await update.message.reply_text(
            "Главное меню:", reply_markup=main_kb()
        )
        return

    if text == "🔙 Назад":
        if section == "gemini_script":
            context.user_data["section"] = S_FARM
            context.user_data.pop("gemini_topic", None)
            context.user_data.pop("gemini_traits", None)
            context.user_data.pop("gemini_script", None)
            context.user_data.pop("gemini_script_text", None)
            await update.message.reply_text(
                "🎬 *Ферма видео*", parse_mode="Markdown", reply_markup=farm_kb()
            )
            return
        if section == S_MODELS and context.user_data.get("models_view"):
            # Из списка провайдеров — обратно в меню моделей, не в ферму.
            context.user_data["models_view"] = None
            await show_models_menu(update, context)
        elif section in (S_FARM, S_MODELS):
            context.user_data["section"] = S_FARM
            await update.message.reply_text(
                "🎬 *Ферма видео*", parse_mode="Markdown", reply_markup=farm_kb()
            )
        elif section == S_VPN:
            context.user_data["section"] = S_VPN
            await show_vpn(update, context)
        else:
            await update.message.reply_text("Главное меню:", reply_markup=main_kb())
        return

    # "✨ Создать сценарий" теперь обрабатывается через ConversationHandler
    # если text == "✨ Создать сценарий":
    #     context.user_data["section"] = "gemini_script"
    #     await update.message.reply_text(
    #         "📝 *Тема для сценария*\n\nНапиши тему, например:\n• VPN и приватность\n• Интернет технологии\n• Кибербезопасность",
    #         parse_mode="Markdown",
    #         reply_markup=topics_kb()
    #     )
    #     return

    if text == "🎬 Создать видео":
        context.user_data["section"] = S_FARM
        await update.message.reply_text(
            "🎬 *Ферма видео*",
            parse_mode="Markdown",
            reply_markup=farm_kb()
        )
        return

    if text == "📦 Пакет видео":
        context.user_data["section"] = S_FARM
        await update.message.reply_text(
            "📦 *Пакет видео*\n\nСколько видео создать?",
            parse_mode="Markdown",
            reply_markup=batch_kb()
        )
        return

    if text == "📤 Загрузить":
        context.user_data["section"] = S_FARM
        await update.message.reply_text(
            "📤 *Загрузка видео*\n\nВыбери платформу:",
            parse_mode="Markdown",
            reply_markup=platform_kb()
        )
        return

    if text == "📁 Список видео":
        await update.message.reply_text("📁 *Список видео*\n\nПока пусто. Создай первое видео!", parse_mode="Markdown")
        return

    if text == "📊 Статус":
        await update.message.reply_text("📊 *Статус*\n\nБот готов к работе!")
        return

    if text == "⚙ Настройки AI":
        context.user_data["section"] = S_MODELS
        await show_models_menu(update, context)
        return

    # Если ничего не подошло
    # await update.message.reply_text(
    #     "Используй кнопки внизу экрана ⬇",
    #     reply_markup=main_kb(),
    # )


# ==================== ФЕРМА ВИДЕО ====================



async def _run_build(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    topic: Optional[str] = None,
    custom_script: Optional[str] = None,
) -> None:
    builder = _builder(context)
    chat_id = update.effective_chat.id

    async def progress(msg: str) -> None:
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=f"\u2699 {msg}", parse_mode="Markdown"
            )
        except Exception:
            pass

    try:
        path = await builder.build(
            topic=topic, custom_script=custom_script,
            progress_callback=progress,
        )

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ *Видео готово!*\n`{_esc(path.name)}`",
            parse_mode="Markdown",
        )
        with open(path, "rb") as f:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=f,
                caption=f"\U0001f3ac {topic or 'Своё видео'} \u2022 {path.name}",
                reply_markup=done_kb(),
            )

        # Auto-post to group if configured
        if settings.telegram_chat_id:
            try:
                with open(path, "rb") as f:
                    await context.bot.send_video(
                        chat_id=settings.telegram_chat_id,
                        video=f,
                        caption=f"\U0001f3ac {topic or 'Своё видео'}",
                    )
            except Exception as e:
                print(f"[AUTO-POST] Failed to send to group: {e}")

    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"\u274c *Ошибка:* `{e}`",
            parse_mode="Markdown",
            reply_markup=farm_kb(),
        )
    finally:
        await builder.cleanup()


async def _run_batch(update: Update, context: ContextTypes.DEFAULT_TYPE, count: int) -> None:
    builder = _builder(context)
    chat_id = update.effective_chat.id

    async def progress(msg: str) -> None:
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=f"\u2699 {msg}", parse_mode="Markdown"
            )
        except Exception:
            pass

    try:
        if builder.scenes_dir.exists():
            shutil.rmtree(builder.scenes_dir)
        builder.scenes_dir.mkdir(parents=True, exist_ok=True)
        paths = await builder.build_batch(count, progress_callback=progress)
        msg = f"✅ *Готово!* Создано {len(paths)} видео:\n"
        for p in paths:
            msg += f"  \u2022 `{p.name}`\n"

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=done_kb(),
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ *Ошибка:* `{e}`",
            parse_mode="Markdown",
            reply_markup=farm_kb(),
        )
    finally:
        await builder.cleanup()


async def _run_upload_text(update: Update, context: ContextTypes.DEFAULT_TYPE, platform: str) -> None:
    output_dir = Path(settings.output_dir)
    mp4_files = sorted(output_dir.glob("*.mp4"), key=os.path.getmtime, reverse=True)

    if not mp4_files:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Нет видео в папке output/. Сначала создай видео.",
            reply_markup=farm_kb(),
        )
        return

    latest = mp4_files[0]
    uploader_map = {
        "tiktok": TikTokUploader,
        "youtube": YouTubeUploader,
        "instagram": InstagramUploader,
    }
    cls = uploader_map.get(platform)
    if not cls:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Неизвестная платформа: {platform}",
            reply_markup=farm_kb(),
        )
        return

    try:
        async with cls() as uploader:
            success = await uploader.upload(latest)
            if success:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"✅ *Загружено на {platform.capitalize()}!*",
                    parse_mode="Markdown",
                    reply_markup=farm_kb(),
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"❌ Не удалось загрузить на {platform.capitalize()}.",
                    reply_markup=farm_kb(),
                )
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ *Ошибка загрузки:* `{e}`",
            parse_mode="Markdown",
            reply_markup=farm_kb(),
        )






# ==================== МОДЕЛИ ====================

def _provider_label(button: str) -> str:
    """'✅ fal' -> 'fal'. Кнопки несут статус префиксом, значение — хвостом."""
    return button.split(" ", 1)[-1].strip() if " " in button else button.strip()


async def show_models_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["section"] = S_MODELS
    context.user_data["models_view"] = None

    chosen = context.user_data.get("video_provider")
    providers = available_video_providers()
    usable = ", ".join(label for label, ok, _ in providers if ok) or "—"

    msg = (
        "🤖 *Модели*\n\n"
        f"🧠 Сценарий: `{settings.llm_model}`\n"
        f"🖼 Картинки: `{settings.gemini_image_model}` + запасные\n"
        f"🎥 Видео: *{chosen or 'авто (цепочка)'}*\n"
        f"🔊 Голос: `{settings.tts_voice}`\n\n"
        f"Доступно для видео: {usable}\n\n"
        "_LLM и картинки берутся из `.env`. Провайдера видео можно "
        "переключить прямо отсюда._"
    )
    await update.message.reply_text(msg, parse_mode="Markdown",
                                    reply_markup=ai_models_kb())


async def handle_models_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    if text == "🔙 В ферму":
        context.user_data["section"] = S_FARM
        context.user_data["models_view"] = None
        await update.message.reply_text(
            "🎬 *Ферма видео*", parse_mode="Markdown", reply_markup=farm_kb()
        )
        return

    if text == "🎥 Видео (Video)":
        context.user_data["models_view"] = "video"
        providers = available_video_providers()
        chosen = context.user_data.get("video_provider")
        lines = [f"{'✅' if ok else '🚫'} `{label}` — {reason}"
                 for label, ok, reason in providers]
        await update.message.reply_text(
            "🎥 *Провайдер видео*\n\n" + "\n".join(lines) +
            f"\n\nСейчас: *{chosen or 'авто (цепочка)'}*\n\n"
            "_Выбранный провайдер идёт первым; локальный движок всё равно "
            "остаётся в конце цепочки, поэтому сборка не сорвётся._",
            parse_mode="Markdown",
            reply_markup=video_provider_kb(providers),
        )
        return

    if text == "🧠 Сценарий (LLM)":
        await update.message.reply_text(
            "🧠 *Сценарий (AI#1)*\n\n"
            f"`LLM_MODEL` = {settings.llm_model}\n"
            f"`LLM_BASE_URL` = {settings.llm_base_url}\n"
            f"Ключ: {'задан' if settings.llm_api_key else '❌ нет'}\n\n"
            "_Меняется в `.env`._",
            parse_mode="Markdown", reply_markup=ai_models_kb(),
        )
        return

    if text == "🖼 Картинки (Image)":
        from core.image_gen import get_image_generator
        chain = getattr(get_image_generator(), "generators", [])
        names = "\n".join(f"  {i}. `{g.__class__.__name__}`"
                          for i, g in enumerate(chain, 1)) or "  —"
        await update.message.reply_text(
            "🖼 *Картинки (AI#2)*\n\nЦепочка провайдеров:\n" + names +
            "\n\n_Порядок задаётся ключами в `.env`._",
            parse_mode="Markdown", reply_markup=ai_models_kb(),
        )
        return

    if text == "⚙ Локальные настройки":
        try:
            import torch
            cuda = "✅ CUDA" if torch.cuda.is_available() else "❌ только CPU"
            torch_v = torch.__version__
        except ImportError:
            cuda, torch_v = "❌ torch не установлен", "—"
        await update.message.reply_text(
            "⚙ *Локально*\n\n"
            f"PyTorch: `{torch_v}` — {cuda}\n"
            f"Пресет качества: `{settings.quality_preset}`\n"
            f"Сила движения: `{settings.motion_intensity}`\n"
            f"Зерно / виньетка: `{settings.motion_grain}` / "
            f"`{settings.motion_vignette}`\n"
            f"Переходы: "
            f"`{'вкл' if settings.transitions_enabled else 'выкл'}"
            f" ({settings.transition_duration}с)`\n"
            f"Громкость: `{settings.loudness_lufs} LUFS`",
            parse_mode="Markdown", reply_markup=ai_models_kb(),
        )
        return

    # ─── Выбор провайдера видео ───
    if context.user_data.get("models_view") == "video":
        if text == "♻ Авто (цепочка)":
            context.user_data["video_provider"] = None
            context.user_data["models_view"] = None
            await update.message.reply_text(
                "♻ Провайдер видео: *авто (цепочка)*",
                parse_mode="Markdown", reply_markup=ai_models_kb(),
            )
            return

        label = _provider_label(text)
        match = next((p for p in available_video_providers() if p[0] == label),
                     None)
        if match:
            _, usable, reason = match
            if not usable:
                await update.message.reply_text(
                    f"🚫 `{label}` недоступен: {reason}",
                    parse_mode="Markdown",
                    reply_markup=video_provider_kb(available_video_providers()),
                )
                return
            context.user_data["video_provider"] = label
            context.user_data["models_view"] = None
            await update.message.reply_text(
                f"✅ Провайдер видео: *{label}*",
                parse_mode="Markdown", reply_markup=ai_models_kb(),
            )
            return

    # await update.message.reply_text("Используй кнопки ⬇",
    #                                 reply_markup=ai_models_kb())


async def toggle_pipeline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Переключить пошаговую сборку и сборку одним заходом."""
    new_mode = MODE_AUTO if _mode(context) == MODE_STEP else MODE_STEP
    context.user_data["pipeline_mode"] = new_mode

    if new_mode == MODE_AUTO:
        msg = (
            "▶️ *Режим: без остановок*\n\n"
            "После выбора темы бот сам пройдёт сценарий → картинки → видео "
            "→ сборку и пришлёт готовый ролик."
        )
    else:
        msg = (
            "⏸ *Режим: по шагам*\n\n"
            "Бот покажет сценарий и картинки и будет спрашивать "
            "подтверждение перед следующим шагом."
        )
    await update.message.reply_text(msg, parse_mode="Markdown",
                                    reply_markup=farm_kb())


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        f"\u2699 *Настройки*\n\n"
        f"`LLM_MODEL` = {settings.llm_model}\n"
        f"`TTS_ENGINE` = {settings.tts_engine}\n"
        f"`VIDEO_SIZE` = {settings.video_width}x{settings.video_height}\n"
        f"`FPS` = {settings.video_fps}\n"
        f"`OUTPUT_DIR` = {settings.output_dir}\n\n"
        f"Изменить можно в `.env` на сервере"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=farm_kb())


# ==================== VPN МОНИТОР ====================









# ==================== STEP-BY-STEP PIPELINE ====================

async def _step1_generate_text(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str) -> None:
    chat_id = update.effective_chat.id
    group_id = settings.telegram_chat_id
    builder = _builder(context)

    try:
        scene_data = await builder.llm.generate_scenes(topic)
        scenes = scene_data.get("scenes", [])
        if not scenes:
            raise RuntimeError("AI #1 вернул пустой сценарий")
        full_text = " ".join(s["narration"] for s in scenes)
        highlight_words = scene_data.get("highlight_words", [])

        context.user_data["pipeline_scenes"] = scenes
        context.user_data["pipeline_highlight_words"] = highlight_words
        context.user_data["pipeline_text"] = full_text

        # Show full scene breakdown
        parts = [f"\U0001f3af *СЦЕНАРИЙ: {_esc(topic)}*"]
        for i, s in enumerate(scenes, 1):
            dur = s.get("duration", 3)
            parts.append(
                f"\n__*Сцена {i}*__ ({dur}с)\n"
                f" *narration:* {_esc(s.get('narration', ''))}\n"
                f" *style:* {_esc(s.get('image_prompt', '')[:200])}"
            )
        await context.bot.send_message(
            chat_id=chat_id,
            text="\n".join(parts),
            parse_mode="Markdown",
        )

        if group_id:
            try:
                msg = await context.bot.send_message(
                    chat_id=group_id,
                    text=f"\U0001f4dd *\u0421\u0446\u0435\u043d\u0430\u0440\u0438\u0439:* {_esc(topic)}\n\n{_esc(full_text)}",
                    parse_mode="Markdown",
                )
                context.user_data["pipeline_group_msg_id"] = msg.message_id
            except Exception as e:
                print(f"[GROUP] Send text failed: {e}")

        await context.bot.send_message(
            chat_id=chat_id,
            text="\u2753 *\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u044f?*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("\u2705 \u0414\u0430", callback_data="pipe_images"),
                InlineKeyboardButton("\u274c \u041d\u0435\u0442", callback_data="pipe_cancel"),
            ]]),
        )
        return AWAIT_AFTER_TEXT

    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"\u274c *\u041e\u0448\u0438\u0431\u043a\u0430 AI#1:* `{_esc(str(e))}`",
            parse_mode="Markdown",
            reply_markup=farm_kb(),
        )
    finally:
        await builder.cleanup()


async def _step2_generate_images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    group_id = settings.telegram_chat_id
    scenes = context.user_data.get("pipeline_scenes", [])
    if not scenes:
        await query.edit_message_text("\u274c *\u041d\u0435\u0442 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u044f*", parse_mode="Markdown")
        return

    await query.edit_message_text(
        "\U0001f5bc AI#2 \u0433\u0435\u043d\u0435\u0440\u0438\u0440\u0443\u044e \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u044f...",
        parse_mode="Markdown",
    )

    builder = _builder(context)
    try:
        # Clear old cached images
        if builder.scenes_dir.exists():
            shutil.rmtree(builder.scenes_dir)
        builder.scenes_dir.mkdir(parents=True, exist_ok=True)

        image_paths = []
        run_seed = secrets.randbelow(2**31)
        for i, scene in enumerate(scenes):
            img_prompt = scene.get("image_prompt", scene["narration"])
            img_path = builder.scenes_dir / f"scene_{i:02d}.jpg"
            scene_seed = (run_seed + i * 104729) % (2**31)
            try:
                await builder.image_gen.generate(img_prompt, img_path, seed=scene_seed)
            except Exception:
                img_path = await builder._generate_fallback_image(
                    scene["narration"], img_path, scene_seed
                )

            # Send image to user's DM
            with open(img_path, "rb") as f:
                scene_text = scene.get('narration', '')[:100]
                caption = f"\U0001f5bc \u0421\u0446\u0435\u043d\u0430 {i+1}/{len(scenes)}\n\n{scene_text}"
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=f,
                    caption=caption,
                )

            image_paths.append(img_path)

            if group_id:
                try:
                    with open(img_path, "rb") as f:
                        await context.bot.send_photo(
                            chat_id=group_id,
                            photo=f,
                            caption=f"\U0001f5bc \u0421\u0446\u0435\u043d\u0430 {i+1}/{len(scenes)}",
                        )
                except Exception as e:
                    print(f"[GROUP] Send image failed: {e}")

        context.user_data["pipeline_image_paths"] = image_paths

        await context.bot.send_message(
            chat_id=chat_id,
            text="\u2753 *\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u0432\u0438\u0434\u0435\u043e?*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("\u2705 \u0414\u0430", callback_data="pipe_video"),
                InlineKeyboardButton("\u274c \u041d\u0435\u0442", callback_data="pipe_cancel"),
            ]]),
        )

    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"\u274c *\u041e\u0448\u0438\u0431\u043a\u0430 AI#2:* `{e}`",
            parse_mode="Markdown",
            reply_markup=farm_kb(),
        )
    finally:
        await builder.cleanup()


async def _step3_generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    group_id = settings.telegram_chat_id
    scenes = context.user_data.get("pipeline_scenes", [])
    image_paths = context.user_data.get("pipeline_image_paths", [])
    highlight_words = context.user_data.get("pipeline_highlight_words", [])

    if not scenes or not image_paths:
        await query.edit_message_text("\u274c *\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445 \u0434\u043b\u044f \u0432\u0438\u0434\u0435\u043e*", parse_mode="Markdown")
        return

    await query.edit_message_text(
        "\U0001f3a5 AI#3 \u0433\u0435\u043d\u0435\u0440\u0438\u0440\u0443\u044e \u0432\u0438\u0434\u0435\u043e...",
        parse_mode="Markdown",
    )

    builder = _builder(context)
    try:
        # Clear old cached scene videos
        scenes_video_dir = builder.scenes_dir / "scene_videos"
        if scenes_video_dir.exists():
            shutil.rmtree(scenes_video_dir)
        scenes_video_dir.mkdir(parents=True, exist_ok=True)

        # Generate scene videos from images
        scene_videos = []
        repair_seed = secrets.randbelow(2**31)
        for i, (scene, img_path) in enumerate(zip(scenes, image_paths)):
            duration = scene.get("duration", 3)
            vid_path = scenes_video_dir / f"scene_video_{i:02d}.mp4"
            if not img_path.exists() or img_path.stat().st_size < 1000:
                img_prompt = scene.get("image_prompt", scene["narration"])
                scene_seed = (repair_seed + i * 104729) % (2**31)
                try:
                    await builder.image_gen.generate(img_prompt, img_path, seed=scene_seed)
                except Exception:
                    await builder._generate_fallback_image(
                        scene["narration"], img_path, scene_seed
                    )
            try:
                await builder.img2video.generate(img_path, scene["image_prompt"], vid_path, duration)
            except Exception:
                await builder._image_to_still_video(img_path, duration, vid_path)
            scene_videos.append(vid_path)

        # TTS
        narration_text = " ".join(s["narration"] for s in scenes)
        audio_path = await builder.tts.synthesize(narration_text)
        audio_duration = await builder.tts.get_audio_duration(audio_path)

        # Subtitle SRT
        track = builder.subtitle_timing.generate(narration_text, audio_duration, highlight_words)
        srt_path = builder._generate_srt(track)

        # CTA image
        cta_path = builder._generate_cta_image()

        # Assemble with ffmpeg
        output_path = builder.output_dir / f"ubt_video_{builder._timestamp()}.mp4"
        await builder._assemble_ffmpeg(scene_videos, audio_path, srt_path, cta_path, output_path, audio_duration)

        # Send to user
        with open(output_path, "rb") as f:
            await context.bot.send_video(
                chat_id=chat_id, video=f,
                caption=f"\U0001f3ac *\u0412\u0438\u0434\u0435\u043e \u0433\u043e\u0442\u043e\u0432\u043e!*",
                parse_mode="Markdown",
                reply_markup=done_kb(),
            )

        # Send to group
        if group_id:
            try:
                with open(output_path, "rb") as f:
                    await context.bot.send_video(
                        chat_id=group_id, video=f,
                        caption=f"\U0001f3ac *\u041d\u043e\u0432\u043e\u0435 \u0432\u0438\u0434\u0435\u043e*",
                        parse_mode="Markdown",
                    )
            except Exception as e:
                print(f"[GROUP] Send video failed: {e}")

    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"\u274c *\u041e\u0448\u0438\u0431\u043a\u0430 AI#3:* `{e}`",
            parse_mode="Markdown",
            reply_markup=farm_kb(),
        )
    finally:
        await builder.cleanup()


async def _handle_pipeline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data
    chat_id = update.effective_chat.id

    if data == "pipe_images":
        await _step2_generate_images(update, context)
    elif data == "pipe_video":
        await _step3_generate_video(update, context)
    elif data == "pipe_cancel":
        await query.answer()
        await query.edit_message_text("\u274c \u041e\u0442\u043c\u0435\u043d\u0435\u043d\u043e")
        await context.bot.send_message(
            chat_id=chat_id,
            text="\u0412\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u044e\u0441\u044c \u0432 \u043c\u0435\u043d\u044e",
            reply_markup=farm_kb(),
        )


# ==================== GEMINI SCRIPT GENERATOR ====================

async def handle_gemini_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c \u0432\u0432\u0451\u043b \u0442\u0435\u043c\u0443 \u2014 \u0437\u0430\u043f\u0440\u0430\u0448\u0438\u0432\u0430\u0435\u043c \u0447\u0435\u0440\u0442\u044b/\u0441\u0442\u0438\u043b\u044c."""
    topic = update.message.text.strip()
    if topic.startswith("/") and topic in ("/cancel", "/start", "/menu"):
        return await cancel(update, context)

    context.user_data["gemini_topic"] = topic
    await update.message.reply_text(
        "\u2728 \u041e\u0442\u043b\u0438\u0447\u043d\u043e! \u0422\u0435\u043c\u0430: *" + _esc(topic) + "*\n\n"
        "\u0422\u0435\u043f\u0435\u0440\u044c \u043d\u0430\u043f\u0438\u0448\u0438 **\u0447\u0435\u0440\u0442\u044b \u0438\u043b\u0438 \u0441\u0442\u0438\u043b\u044c** \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u044f (\u043d\u0435\u043e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u043e):\n"
        "\u2014 \u043d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: \u00ab\u044e\u043c\u043e\u0440\u0438\u0441\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u0439\u00bb, \u00ab\u043d\u0430\u0443\u0447\u043d\u044b\u0439\u00bb, \u00ab\u0434\u043b\u044f \u0434\u0435\u0442\u0435\u0439\u00bb, \u00ab\u0441 \u044d\u043c\u043e\u0434\u0437\u0438\u00bb\n"
        "\u0418\u043b\u0438 \u043e\u0442\u043f\u0440\u0430\u0432\u044c /skip \u0447\u0442\u043e\u0431\u044b \u043f\u0440\u043e\u043f\u0443\u0441\u0442\u0438\u0442\u044c:",
        parse_mode="Markdown",
        reply_markup=remove_kb(),
    )
    return AWAIT_TRAITS


async def handle_gemini_traits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c \u0432\u0432\u0451\u043b \u0447\u0435\u0440\u0442\u044b \u0438\u043b\u0438 \u043f\u0440\u043e\u043f\u0443\u0441\u0442\u0438\u043b \u2014 \u0433\u0435\u043d\u0435\u0440\u0438\u0440\u0443\u0435\u043c \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0439."""
    text = update.message.text.strip()
    if text == "/skip":
        context.user_data["gemini_traits"] = None
    elif text.startswith("/"):
        return await cancel(update, context)
    else:
        context.user_data["gemini_traits"] = text

    topic = context.user_data.get("gemini_topic", "\u043e\u0431\u0449\u0430\u044f \u0442\u0435\u043c\u0430")
    traits = context.user_data.get("gemini_traits")

    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"[INFO] \u0413\u0435\u043d\u0435\u0440\u0438\u0440\u0443\u044e \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0439 \u043d\u0430 \u0442\u0435\u043c\u0443 \u00ab{_esc(topic)}\u00bb...",
        parse_mode="Markdown",
        reply_markup=remove_kb(),
    )

    try:
        gemini = GeminiClient()
        script = await gemini.generate_script(topic, traits)
        context.user_data["gemini_script"] = script
        context.user_data["gemini_script_text"] = script.get("text", "")

        hook = script.get("hook", "")
        highlights = script.get("highlight_words", [])
        script_text = script.get("text", "")

        msg = f"[INFO] *\u0421\u0426\u0415\u041d\u0410\u0420\u0418\u0419*\n\n"
        if hook:
            msg += f"Hook: `{_esc(hook)}`\n\n"
        msg += f"`{_esc(script_text)}`\n\n"
        if highlights:
            msg += f" \u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u0441\u043b\u043e\u0432\u0430: {', '.join(f'`{h}`' for h in highlights)}\n"
        msg += "\n\u0427\u0442\u043e \u0434\u0435\u043b\u0430\u0435\u043c \u0434\u0430\u043b\u044c\u0448\u0435?"

        await context.bot.send_message(
            chat_id=chat_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=gemini_script_kb(),
        )
        return AWAIT_SCRIPT_ACTION

    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"[ERROR] \u041e\u0448\u0438\u0431\u043a\u0430 \u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u0438: `{_esc(str(e))}`\n\u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439 \u0435\u0449\u0451 \u0440\u0430\u0437.",
            parse_mode="Markdown",
            reply_markup=farm_kb(),
        )
        return ConversationHandler.END


async def handle_gemini_action(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> int:
    """\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0439 \u043f\u043e\u0441\u043b\u0435 \u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u0438 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u044f."""
    chat_id = update.effective_chat.id
    topic = context.user_data.get("gemini_topic", "")
    traits = context.user_data.get("gemini_traits")
    old_text = context.user_data.get("gemini_script_text", "")

    if text == "\u041f\u0435\u0440\u0435\u0434\u0435\u043b\u0430\u0442\u044c":
        await context.bot.send_message(
            chat_id=chat_id,
            text="[INFO] \u041f\u0435\u0440\u0435\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u0443\u044e \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0439...",
            reply_markup=remove_kb(),
        )
        try:
            gemini = GeminiClient()
            script = await gemini.regenerate_script(old_text, topic, traits)
            context.user_data["gemini_script"] = script
            context.user_data["gemini_script_text"] = script.get("text", "")

            hook = script.get("hook", "")
            highlights = script.get("highlight_words", [])
            text_content = script.get("text", "")

            msg = f"[INFO] *\u041d\u041e\u0412\u042b\u0419 \u0421\u0426\u0415\u041d\u0410\u0420\u0418\u0419*\n\n"
            if hook:
                msg += f"Hook: `{_esc(hook)}`\n\n"
            msg += f"`{_esc(text_content)}`\n\n"
            if highlights:
                msg += f"\u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u0441\u043b\u043e\u0432\u0430: {', '.join(f'`{h}`' for h in highlights)}\n"
            msg += "\n\u0427\u0442\u043e \u0434\u0435\u043b\u0430\u0435\u043c \u0434\u0430\u043b\u044c\u0448\u0435?"

            await context.bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode="Markdown",
                reply_markup=gemini_script_kb(),
            )
            return AWAIT_SCRIPT_ACTION
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"[ERROR] \u041e\u0448\u0438\u0431\u043a\u0430: `{_esc(str(e))}`",
                parse_mode="Markdown",
                reply_markup=gemini_script_kb(),
            )
            return AWAIT_SCRIPT_ACTION

    if text == "\u0421\u0432\u043e\u0439 \u0442\u0435\u043a\u0441\u0442":
        await context.bot.send_message(
            chat_id=chat_id,
            text="[INFO] \u041d\u0430\u043f\u0438\u0448\u0438 \u0441\u0432\u043e\u0439 \u0442\u0435\u043a\u0441\u0442 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u044f (\u0438\u043b\u0438 /cancel):",
            parse_mode="Markdown",
            reply_markup=remove_kb(),
        )
        return AWAIT_CUSTOM_TEXT

    if text == "\u25b6\ufe0f \u041f\u0435\u0440\u0435\u0439\u0442\u0438 \u043a \u043a\u0430\u0440\u0442\u0438\u043d\u043a\u0430\u043c":
        # \u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u043c \u0442\u0435\u043a\u0443\u0449\u0438\u0439 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0439 \u0434\u043b\u044f \u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u0438 \u0432\u0438\u0434\u0435\u043e
        script_text = context.user_data.get("gemini_script_text", "")
        if not script_text:
            await context.bot.send_message(
                chat_id=chat_id,
                text="\u274c \u041d\u0435\u0442 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u044f. \u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0441\u043e\u0437\u0434\u0430\u0439 \u0435\u0433\u043e.",
                reply_markup=farm_kb(),
            )
            return ConversationHandler.END

        await context.bot.send_message(
            chat_id=chat_id,
            text="\ud83d\uddbc\ufe0f \u0420\u0430\u0437\u0431\u0438\u0432\u0430\u044e \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0439 \u043d\u0430 \u0441\u0446\u0435\u043d\u044b \u0438 \u0433\u0435\u043d\u0435\u0440\u0438\u0440\u0443\u044e \u043a\u0430\u0440\u0442\u0438\u043d\u043a\u0438...",
            reply_markup=remove_kb(),
        )
        asyncio.create_task(_run_gemini_to_video(update, context, script_text))
        return ConversationHandler.END

    if text == " \u041e\u0442\u043c\u0435\u043d\u0430":
        await context.bot.send_message(
            chat_id=chat_id,
            text="\u041e\u0442\u043c\u0435\u043d\u0435\u043d\u043e. \u0412\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u044e\u0441\u044c \u0432 \u043c\u0435\u043d\u044e.",
            reply_markup=farm_kb(),
        )
        return ConversationHandler.END

    return AWAIT_SCRIPT_ACTION


async def _run_gemini_to_video(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    script_text: str,
) -> None:
    """\u0420\u0430\u0437\u0431\u0438\u0442\u044c \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0439 \u043d\u0430 \u0441\u0446\u0435\u043d\u044b \u0438 \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c \u043f\u0430\u0439\u043f\u043b\u0430\u0439\u043d \u0441\u0431\u043e\u0440\u043a\u0438."""
    chat_id = update.effective_chat.id
    builder = _builder(context)

    try:
        # \u0420\u0430\u0437\u0431\u0438\u0432\u0430\u0435\u043c \u043d\u0430 \u0441\u0446\u0435\u043d\u044b \u0447\u0435\u0440\u0435\u0437 Gemini
        gemini = GeminiClient()
        scene_data = await gemini.break_into_scenes(script_text)
        scenes = scene_data.get("scenes", [])

        if not scenes:
            raise RuntimeError("Gemini \u0432\u0435\u0440\u043d\u0443\u043b \u043f\u0443\u0441\u0442\u043e\u0439 \u0441\u043f\u0438\u0441\u043e\u043a \u0441\u0446\u0435\u043d")

        # \u0421\u043e\u0445\u0440\u0430\u043d\u044f\u0435\u043c \u0432 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442 \u0434\u043b\u044f \u043f\u0430\u0439\u043f\u043b\u0430\u0439\u043d\u0430
        context.user_data["pipeline_scenes"] = scenes
        highlight_words = context.user_data.get("gemini_script", {}).get("highlight_words", [])
        context.user_data["pipeline_highlight_words"] = highlight_words

        # \u0417\u0430\u043f\u0443\u0441\u043a\u0430\u0435\u043c \u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u044e \u043a\u0430\u0440\u0442\u0438\u043d\u043e\u043a (step 2)
        image_paths = []
        import secrets
        run_seed = secrets.randbelow(2**31)
        for i, scene in enumerate(scenes):
            img_prompt = scene.get("image_prompt", scene.get("narration", ""))
            img_path = builder.scenes_dir / f"scene_{i:02d}.jpg"
            scene_seed = (run_seed + i * 104729) % (2**31)
            try:
                await builder.image_gen.generate(img_prompt, img_path, seed=scene_seed)
            except Exception:
                img_path = await builder._generate_fallback_image(
                    scene.get("narration", ""), img_path, scene_seed
                )

            with open(img_path, "rb") as f:
                caption = f"\ufe0f \u0421\u0446\u0435\u043d\u0430 {i+1}/{len(scenes)}\n\n{scene.get('narration', '')[:100]}"
                await context.bot.send_photo(chat_id=chat_id, photo=f, caption=caption)

            image_paths.append(img_path)

        context.user_data["pipeline_image_paths"] = image_paths

        # \u0421\u043f\u0440\u0430\u0448\u0438\u0432\u0430\u0435\u043c \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435 \u0434\u043b\u044f \u0432\u0438\u0434\u0435\u043e
        await context.bot.send_message(
            chat_id=chat_id,
            text="\u2753 *\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u0432\u0438\u0434\u0435\u043e \u0438\u0437 \u044d\u0442\u0438\u0445 \u043a\u0430\u0440\u0442\u0438\u043d\u043e\u043a?*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("\u2705 \u0414\u0430", callback_data="pipe_video"),
                InlineKeyboardButton("\u274c \u041d\u0435\u0442", callback_data="pipe_cancel"),
            ]]),
        )

    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"\u274c \u041e\u0448\u0438\u0431\u043a\u0430: `{_esc(str(e))}`",
            parse_mode="Markdown",
            reply_markup=farm_kb(),
        )
    finally:
        await builder.cleanup()


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отменено.", reply_markup=main_kb())
    return ConversationHandler.END


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    import traceback
    traceback.print_exception(type(context.error), context.error, context.error.__traceback__)
    try:
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"\u26a0 Ошибка: `{context.error}`",
                parse_mode="Markdown",
            )
    except Exception:
        pass
