"""
Полный тест генерации видео с проверкой уникальности картинок.
"""
import asyncio
import hashlib
from pathlib import Path
from video_engine.builder import VideoBuilder

async def main():
    print("=== Полный тест генерации видео ===\n")

    builder = VideoBuilder()

    print("Генерирую видео на тему 'блокчейн'...")
    try:
        output = await builder.build(topic="блокчейн")
        print(f"\n✓ Видео создано: {output}")
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        return

    # Проверяем картинки
    scenes_dir = builder.scenes_dir
    images = sorted(scenes_dir.glob("scene_*.jpg"))

    print(f"\n=== Проверка уникальности {len(images)} картинок ===")

    hashes = {}
    for img in images:
        data = img.read_bytes()
        h = hashlib.md5(data).hexdigest()[:12]
        size = len(data)
        hashes[img.name] = h
        print(f"  {img.name}: {size:6d} bytes, md5={h}")

    unique = len(set(hashes.values()))
    print(f"\n✓ Уникальных: {unique}/{len(images)}")

    if unique < len(images):
        print("⚠ ПОВТОРЫ НАЙДЕНЫ:")
        seen = {}
        for name, h in hashes.items():
            if h not in seen:
                seen[h] = [name]
            else:
                seen[h].append(name)
        for h, names in seen.items():
            if len(names) > 1:
                print(f"  md5={h}: {', '.join(names)}")
    else:
        print("✓ Все картинки уникальны!")

if __name__ == "__main__":
    asyncio.run(main())
