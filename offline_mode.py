#!/usr/bin/env python3
"""
Offline mode for UBT Bot 2 — работает без VPN сервера.
Использует:
- Gemini API для сценариев
- Локальную генерацию изображений (pixel art fallback)
- Локальный motion engine для видео
- edge-tts для озвучки
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings


def check_offline_deps():
    """Проверяем зависимости для офлайн-режима."""
    print("=" * 60)
    print("ПРОВЕРКА ЗАВИСИМОСТЕЙ ДЛЯ ОФЛАЙН-РЕЖИМА")
    print("=" * 60)

    # Gemini API ключи
    gemini_keys = [k.strip() for k in settings.gemini_api_keys.split(",") if k.strip()]
    if gemini_keys:
        print(f"[OK] Gemini API ключей: {len(gemini_keys)}")
    else:
        print("[FAIL] Нет Gemini API ключей! Добавьте GEMINI_API_KEYS в .env")
        return False

    # edge-tts (не требует ключа)
    print(f"[OK] TTS engine: {settings.tts_engine}")

    # Проверяем директории
    from pathlib import Path
    output_dir = Path(settings.output_dir)
    bg_dir = Path(settings.backgrounds_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    bg_dir.mkdir(parents=True, exist_ok=True)
    print(f"[OK] output_dir: {output_dir.absolute()}")
    print(f"[OK] backgrounds_dir: {bg_dir.absolute()}")

    # Проверяем ffmpeg
    try:
        import subprocess
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        if result.returncode == 0:
            print("[OK] ffmpeg установлен")
        else:
            print("[WARN] ffmpeg не найден — видео не будет собираться")
    except FileNotFoundError:
        print("[WARN] ffmpeg не установлен — скачайте с https://ffmpeg.org/download.html")
        print("       Для Windows: раскомментируйте platform-tools.zip в проекте")

    print("\n[OK] Все зависимости для офлайн-режима готовы!\n")
    return True


async def test_offline_pipeline():
    """Тестируем полный офлайн-пайплайн: сценарий -> картинки -> видео."""
    print("=" * 60)
    print("ТЕСТ ОФЛАЙН-ПАЙПЛАЙНА")
    print("=" * 60)

    from core.gemini_client import GeminiClient
    from video_engine.builder import VideoBuilder

    topic = "VPN безопасность"
    traits = "серьёзный, с фактами"

    print(f"\n1. Генерирую сценарий на тему: {topic}")
    try:
        gemini = GeminiClient()
        script = await gemini.generate_script(topic, traits)
        print(f"   [OK] Сценарий: {script['text'][:80]}...")
        print(f"   Hook: {script.get('hook', 'N/A')}")
    except Exception as e:
        print(f"   [FAIL] Ошибка генерации сценария: {e}")
        return False

    print(f"\n2. Создаю видео через builder...")
    builder = VideoBuilder()
    try:
        path = await builder.build(topic=topic, custom_script=script["text"])
        print(f"   [OK] Видео создано: {path}")
        print(f"   Размер: {path.stat().st_size / 1024 / 1024:.1f} MB")
        return True
    except Exception as e:
        print(f"   [FAIL] Ошибка создания видео: {e}")
        return False
    finally:
        await builder.cleanup()


async def interactive_offline():
    """Интерактивный офлайн-режим: пользователь вводит тему, получает видео."""
    print("=" * 60)
    print("ИНТЕРАКТИВНЫЙ ОФЛАЙН-РЕЖИМ")
    print("=" * 60)
    print("Введите тему для видео (или 'exit' для выхода):")

    from core.gemini_client import GeminiClient
    from video_engine.builder import VideoBuilder

    while True:
        topic = input("\nТема: ").strip()
        if topic.lower() in ("exit", "quit", "выход"):
            print("Выход из офлайн-режима.")
            break
        if not topic:
            continue

        traits = input("Черты/стиль (Enter чтобы пропустить): ").strip() or None

        print(f"\nГенерирую видео на тему '{topic}'...")
        try:
            gemini = GeminiClient()
            script = await gemini.generate_script(topic, traits)
            print(f"Сценарий: {script['text'][:100]}...")

            builder = VideoBuilder()
            path = await builder.build(topic=topic, custom_script=script["text"])
            print(f"Видео готово: {path}")
            print(f"Размер: {path.stat().st_size / 1024 / 1024:.1f} MB\n")
            await builder.cleanup()

        except Exception as e:
            print(f"Ошибка: {e}\n")


async def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        if check_offline_deps():
            success = await test_offline_pipeline()
            sys.exit(0 if success else 1)
        else:
            sys.exit(1)
    elif len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        if check_offline_deps():
            await interactive_offline()
        else:
            sys.exit(1)
    else:
        print("Использование:")
        print("  python offline_mode.py --test          # Тест офлайн-пайплайна")
        print("  python offline_mode.py --interactive   # Интерактивный режим")
        print("  python offline_mode.py --check         # Проверить зависимости")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
