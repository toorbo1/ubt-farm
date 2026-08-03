import asyncio
import os
import re
from pathlib import Path
from typing import Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config.settings import settings
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
)
from .vpn_handlers import vpn_fetch_data

AWAIT_CUSTOM_TEXT, AWAIT_VPN_SERVER, AWAIT_AFTER_TEXT, AWAIT_AFTER_IMAGES = range(4)

ALLOWED_USERS = set()

def _esc(text: str) -> str:
    """Escape Markdown special chars for parse_mode=Markdown."""
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!])", r"\\\1", text)

# ─── Состояния навигации ───
S_MAIN = "main"
S_FARM = "farm"
S_VPN = "vpn"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ALLOWED_USERS.add(user.id)
    context.user_data["section"] = S_MAIN
    await update.message.reply_text(
        f"🚀 *Добро пожаловать!* 🚀\n\n"
        f"Привет, {user.first_name}!\n"
        f"Это бот для управления фермой видео и мониторинга VPN.\n\n"
        f"🎬 *Ферма видео* — генерация и загрузка роликов\n"
        f"📡 *VPN монитор* — статус VPN-серверов\n\n"
        f"Просто нажимай кнопки внизу \u2b07",
        parse_mode="Markdown",
        reply_markup=main_kb(),
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    section = context.user_data.get("section", S_MAIN)

    # ─── Глобальные кнопки ───
    if text == "🔙 В главное меню":
        context.user_data["section"] = S_MAIN
        await update.message.reply_text(
            "Главное меню:", reply_markup=main_kb()
        )
        return

    if text == "🔙 Назад":
        if section == S_FARM:
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

    # ─── Главное меню ───
    if text == "🎬 Ферма видео":
        context.user_data["section"] = S_FARM
        await update.message.reply_text(
            "🎬 *Ферма видео*\n\n"
            "Генерируй видео и загружай на TikTok / YouTube / Instagram.",
            parse_mode="Markdown",
            reply_markup=farm_kb(),
        )
        return

    if text == "📡 VPN монитор":
        context.user_data["section"] = S_VPN
        await show_vpn(update, context)
        return

    # ─── Раздел: Ферма видео ───
    if section == S_FARM:
        await handle_farm_text(update, context, text)
        return

    # ─── Раздел: VPN ───
    if section == S_VPN:
        await handle_vpn_text(update, context, text)
        return

    # Если ничего не подошло
    await update.message.reply_text(
        "Используй кнопки внизу экрана \u2b07",
        reply_markup=main_kb(),
    )


# ==================== ФЕРМА ВИДЕО ====================

async def handle_farm_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    if text == "🎬 Создать видео":
        await update.message.reply_text(
            "🎬 *Выбери тему:*",
            parse_mode="Markdown",
            reply_markup=topics_kb(),
        )
        return

    if text == "📦 Пакет видео":
        await update.message.reply_text(
            "📦 *Сколько видео сделать?*",
            parse_mode="Markdown",
            reply_markup=batch_kb(),
        )
        return

    if text == "📤 Загрузить":
        await update.message.reply_text(
            "📤 *Куда загрузить?*",
            parse_mode="Markdown",
            reply_markup=platform_kb(),
        )
        return

    if text == "📁 Список видео":
        await list_videos(update, context)
        return

    if text == "📊 Статус":
        await farm_status(update, context)
        return

    if text == "⚙ Настройки":
        await show_settings(update, context)
        return

    # ─── Выбор темы ───
    topic_map = {
        "VPN и приватность": "VPN и приватность",
        "Интернет технологии": "интернет технологии",
        "Кибербезопасность": "кибербезопасность",
        "Лайфхаки": "лайфхаки",
        "Гейминг": "гейминг",
    }
    if text in topic_map:
        topic = topic_map[text]
        context.user_data["pipeline_topic"] = topic
        await update.message.reply_text(
            f"🎬 Шаг 1: генерирую текст на тему *{topic}*...",
            parse_mode="Markdown",
            reply_markup=remove_kb(),
        )
        asyncio.create_task(_step1_generate_text(update, context, topic))
        return

    if text == "✏ Свой текст":
        await update.message.reply_text(
            "✏ *Напиши свой текст для видео*\n"
            "(или отправь /cancel):",
            parse_mode="Markdown",
            reply_markup=remove_kb(),
        )
        return AWAIT_CUSTOM_TEXT

    # ─── Выбор количества пакета ───
    batch_map = {
        "3 видео": 3,
        "5 видео": 5,
        "10 видео": 10,
    }
    if text in batch_map:
        count = batch_map[text]
        await update.message.reply_text(
            f"📦 Генерирую *{count} видео*... Это может занять несколько минут.",
            parse_mode="Markdown",
            reply_markup=remove_kb(),
        )
        asyncio.create_task(_run_batch(update, context, count))
        return

    # ─── Выбор платформы ───
    platform_map = {
        "TikTok": "tiktok",
        "YouTube": "youtube",
        "Instagram": "instagram",
    }
    if text in platform_map:
        platform = platform_map[text]
        await update.message.reply_text(
            f"📤 Загружаю на *{text}*...",
            parse_mode="Markdown",
            reply_markup=remove_kb(),
        )
        asyncio.create_task(_run_upload_text(update, context, platform))
        return

    await update.message.reply_text("Используй кнопки \u2b07", reply_markup=farm_kb())


async def custom_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "/cancel":
        await update.message.reply_text(
            "Отменено.", reply_markup=farm_kb()
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "🎬 Генерирую видео с твоим текстом...",
        reply_markup=remove_kb(),
    )
    asyncio.create_task(_run_build(update, context, custom_script=text))
    return ConversationHandler.END


async def _run_build(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    topic: Optional[str] = None,
    custom_script: Optional[str] = None,
) -> None:
    builder = VideoBuilder()
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
    builder = VideoBuilder()
    import shutil
    if builder.scenes_dir.exists():
        shutil.rmtree(builder.scenes_dir)
    builder.scenes_dir.mkdir(parents=True, exist_ok=True)
    chat_id = update.effective_chat.id

    async def progress(msg: str) -> None:
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=f"\u2699 {msg}", parse_mode="Markdown"
            )
        except Exception:
            pass

    try:
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


async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    output_dir = Path(settings.output_dir)
    mp4_files = sorted(output_dir.glob("*.mp4"), key=os.path.getmtime, reverse=True)

    if not mp4_files:
        msg = "📁 Нет готовых видео."
    else:
        msg = f"📁 *Готовые видео ({len(mp4_files)}):*\n\n"
        total_size = sum(f.stat().st_size for f in mp4_files)
        msg += f"Всего: {total_size / 1024 / 1024:.1f} MB\n\n"
        for i, f in enumerate(mp4_files[:15], 1):
            size_mb = f.stat().st_size / 1024 / 1024
            msg += f"{i}. `{f.name}` ({size_mb:.1f} MB)\n"
        if len(mp4_files) > 15:
            msg += f"\n... и ещё {len(mp4_files) - 15} файлов"

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=farm_kb())


async def farm_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    output_dir = Path(settings.output_dir)
    bg_dir = Path(settings.backgrounds_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    bg_dir.mkdir(parents=True, exist_ok=True)

    video_count = len(list(output_dir.glob("*.mp4")))
    bg_count = len(list(bg_dir.glob("*")))
    total_size = sum(f.stat().st_size for f in output_dir.glob("*.mp4"))

    msg = (
        f"📊 *Статус фермы*\n\n"
        f"📁 Видео готово: {video_count}\n"
        f"🎬 Фонов в библиотеке: {bg_count}\n"
        f"💾 Общий вес: {total_size / 1024 / 1024:.1f} MB\n"
        f"🤖 LLM: {settings.llm_model}\n"
        f"🔊 TTS: {settings.tts_engine}\n"
        f"📤 Куда загружаем: TikTok / YouTube / Instagram\n"
        f"📺 Разрешение: {settings.video_width}x{settings.video_height}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=farm_kb())


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

async def show_vpn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📡 Загружаю статус серверов...",
        reply_markup=remove_kb(),
    )
    asyncio.create_task(_fetch_and_show_vpn(update, context))


async def _fetch_and_show_vpn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        servers = await vpn_fetch_data()
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ *Ошибка VPN API:* `{e}`",
            parse_mode="Markdown",
            reply_markup=main_kb(),
        )
        return

    if not servers:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="📡 *VPN монитор*\n\nНет данных от серверов.",
            parse_mode="Markdown",
            reply_markup=vpn_kb(),
        )
        return

    online = sum(1 for s in servers if s.get("status") == "online")
    offline = len(servers) - online
    text = (
        f"📡 *VPN монитор*\n\n"
        f"\U0001F7E2 Online: {online}    \U0001F534 Offline: {offline}\n"
        f"Всего: {len(servers)} серверов\n\n"
    )

    # Топ-10 с пингом
    sorted_servers = sorted(servers, key=lambda s: s.get("ping_ms", 9999) if s.get("status") == "online" else 9999)
    for s in sorted_servers[:10]:
        name = s.get("server_name", s.get("host", "?"))
        ping = s.get("ping_ms")
        icon = "\U0001F7E2" if s.get("status") == "online" else "\U0001F534"
        ping_str = f" ({ping}ms)" if ping is not None else ""
        text += f"{icon} `{name}`{ping_str}\n"

    if len(servers) > 10:
        text += f"\n... и ещё {len(servers) - 10} серверов"

    text += "\n\n_Нажми на сервер ниже для деталей_"

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode="Markdown",
        reply_markup=vpn_servers_inline(servers),
    )
    # После inline-клавиатуры возвращаем reply-кнопки в новом сообщении
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Действия:",
        reply_markup=vpn_kb(),
    )


async def handle_vpn_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    if text == "🔄 Обновить":
        await update.message.reply_text(
            "🔄 Обновляю...", reply_markup=remove_kb()
        )
        asyncio.create_task(_fetch_and_show_vpn(update, context))
        return

    if text == "📊 Статистика":
        await update.message.reply_text(
            "📊 Загружаю статистику...", reply_markup=remove_kb()
        )
        asyncio.create_task(_show_vpn_stats(update, context))
        return

    await update.message.reply_text("Используй кнопки \u2b07", reply_markup=vpn_kb())


async def _show_vpn_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        import ssl
        import httpx
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        async with httpx.AsyncClient(verify=ctx, timeout=15.0) as client:
            resp = await client.get(
                f"{settings.vpn_api_url}/api/stats",
                headers={"X-API-Key": settings.vpn_api_key},
            )
            resp.raise_for_status()
            stats = resp.json()

        total = stats.get("total", 0)
        online = stats.get("online", 0)
        offline = total - online
        avg_ping = stats.get("avg_ping", "\u2014")
        last_update = stats.get("last_update", 0)
        uptime_pct = (online / total * 100) if total > 0 else 0

        text = (
            f"📊 *VPN монитор \u2014 Статистика*\n\n"
            f"Всего проверок (за час): {total}\n"
            f"\U0001F7E2 Online: {online}\n"
            f"\U0001F534 Offline: {offline}\n"
            f"Uptime: {uptime_pct:.1f}%\n"
            f"Средний пинг: {avg_ping}ms\n"
        )

        from datetime import datetime
        if isinstance(last_update, (int, float)) and last_update > 0:
            text += f"Последнее обновление: {datetime.fromtimestamp(last_update).strftime('%Y-%m-%d %H:%M:%S')}"

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode="Markdown",
            reply_markup=vpn_kb(),
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ *Ошибка:* `{e}`",
            parse_mode="Markdown",
            reply_markup=vpn_kb(),
        )


# ==================== STEP-BY-STEP PIPELINE ====================

async def _step1_generate_text(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str) -> None:
    chat_id = update.effective_chat.id
    group_id = settings.telegram_chat_id
    builder = VideoBuilder()

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

    builder = VideoBuilder()
    import shutil
    if builder.scenes_dir.exists():
        shutil.rmtree(builder.scenes_dir)
    builder.scenes_dir.mkdir(parents=True, exist_ok=True)
    try:
        image_paths = []
        for i, scene in enumerate(scenes):
            img_prompt = scene.get("image_prompt", scene["narration"])
            img_path = builder.scenes_dir / f"scene_{i:02d}.jpg"
            if not img_path.exists() or img_path.stat().st_size < 1000:
                if img_path.exists():
                    img_path.unlink()
                try:
                    await builder.image_gen.generate(img_prompt, img_path)
                except Exception:
                    img_path = await builder._generate_fallback_image(scene["narration"], img_path)

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

    builder = VideoBuilder()
    import shutil
    if builder.scenes_dir.exists():
        shutil.rmtree(builder.scenes_dir)
    builder.scenes_dir.mkdir(parents=True, exist_ok=True)
    try:
        # Generate scene videos from images
        scene_videos = []
        for i, (scene, img_path) in enumerate(zip(scenes, image_paths)):
            duration = scene.get("duration", 3)
            vid_path = builder.scenes_dir / f"scene_video_{i:02d}.mp4"
            if not vid_path.exists() or vid_path.stat().st_size < 1000:
                if vid_path.exists():
                    vid_path.unlink()
                try:
                    await builder.img2video.generate(img_path, scene["image_prompt"], vid_path, duration)
                except Exception:
                    vid_path = await builder._image_to_still_video(img_path, duration, vid_path)
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
