"""
Точка входа для UBT Traffic Farm.
Оркестрирует полный пайплайн:
  1. Генерация видео (LLM + TTS + фон + субтитры + CTA + уникализация)
  2. (Опционально) Постинг на платформы

Использование:
  python main.py build --topic "интернет" --count 3
  python main.py build --script "Текст видео..." --background ./bg.mp4
  python main.py upload --video ./output/video.mp4 --platform tiktok
  python main.py pipeline --topic "кибербезопасность" --platform tiktok,youtube
"""
import argparse
import asyncio
import sys
from pathlib import Path

from video_engine.builder import VideoBuilder
from uploader.tiktok import TikTokUploader
from uploader.youtube import YouTubeUploader
from uploader.instagram import InstagramUploader


def cmd_bot(args: argparse.Namespace) -> None:
    """Запуск Telegram-бота."""
    from bot.run_bot import main as bot_main
    bot_main()


async def cmd_build(args: argparse.Namespace) -> None:
    builder = VideoBuilder()
    try:
        if args.count:
            paths = await builder.build_batch(
                count=args.count,
                topics=args.topic.split(",") if args.topic else None,
            )
            for p in paths:
                print(f"  ✓ {p}")
        else:
            path = await builder.build(
                topic=args.topic,
                custom_script=args.script,
                background_path=Path(args.background) if args.background else None,
            )
            print(f"  ✓ {path}")
    finally:
        await builder.cleanup()


async def cmd_upload(args: argparse.Namespace) -> None:
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"✗ Video not found: {video_path}")
        sys.exit(1)

    platforms = args.platform.split(",")
    for platform in platforms:
        platform = platform.strip().lower()
        print(f"[Upload] Uploading to {platform}...")

        uploader_map = {
            "tiktok": TikTokUploader,
            "youtube": YouTubeUploader,
            "instagram": InstagramUploader,
            "reels": InstagramUploader,
            "shorts": YouTubeUploader,
        }
        uploader_cls = uploader_map.get(platform)
        if not uploader_cls:
            print(f"✗ Unknown platform: {platform}")
            continue

        async with uploader_cls() as uploader:
            success = await uploader.upload(
                video_path,
                description=args.description or "",
                hashtags=args.hashtags.split(",") if args.hashtags else None,
            )
            if success:
                print(f"  ✓ Uploaded to {platform}")
            else:
                print(f"  ✗ Failed to upload to {platform}")


async def cmd_pipeline(args: argparse.Namespace) -> None:
    """Полный пайплайн: генерация + загрузка."""
    builder = VideoBuilder()
    try:
        path = await builder.build(topic=args.topic)
    finally:
        await builder.cleanup()

    platforms = args.platform.split(",")
    for platform in platforms:
        platform = platform.strip().lower()
        print(f"[Pipeline] Uploading to {platform}...")
        uploader_map = {
            "tiktok": TikTokUploader,
            "youtube": YouTubeUploader,
            "instagram": InstagramUploader,
        }
        uploader_cls = uploader_map.get(platform)
        if not uploader_cls:
            continue
        async with uploader_cls() as uploader:
            await uploader.upload(path, description=args.description or "")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="UBT Traffic Farm — автоматизированная ферма контента"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # build
    build_p = subparsers.add_parser("build", help="Сгенерировать видео")
    build_p.add_argument("--topic", help="Тема видео")
    build_p.add_argument("--script", help="Свой текст (вместо LLM)")
    build_p.add_argument("--background", help="Путь к фоновому видео")
    build_p.add_argument("--count", type=int, default=0, help="Сколько видео сделать")

    # upload
    upload_p = subparsers.add_parser("upload", help="Загрузить существующее видео")
    upload_p.add_argument("--video", required=True, help="Путь к .mp4")
    upload_p.add_argument("--platform", required=True, help="tiktok, youtube, instagram")
    upload_p.add_argument("--description", help="Описание")
    upload_p.add_argument("--hashtags", help="Хештеги через запятую")

    # pipeline
    pipe_p = subparsers.add_parser("pipeline", help="Полный цикл: генерация + upload")
    pipe_p.add_argument("--topic", help="Тема видео")
    pipe_p.add_argument("--platform", default="tiktok", help="Куда загружать")
    pipe_p.add_argument("--description", default="", help="Описание")

    # bot
    bot_p = subparsers.add_parser("bot", help="Запустить Telegram-бота")
    bot_p.add_argument("--token", help="Telegram Bot API token")
    bot_p.add_argument("--bot", type=int, choices=[1, 2], default=1,
                       help="Bot 1 (оригинальный) или Bot 2 (новый)")

    args = parser.parse_args()

    if args.command == "build":
        asyncio.run(cmd_build(args))
    elif args.command == "upload":
        asyncio.run(cmd_upload(args))
    elif args.command == "pipeline":
        asyncio.run(cmd_pipeline(args))
    elif args.command == "bot":
        cmd_bot(args)


if __name__ == "__main__":
    main()
