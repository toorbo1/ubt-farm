"""
Тест уникальности промптов и картинок после деплоя.
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent))

from core.llm_client import LLMClient

async def main():
    llm = LLMClient()

    print("=== Тест 1: Уникальность промптов ===")
    topic = "искусственный интеллект"

    # Генерируем сцены 3 раза
    for run in range(3):
        result = await llm.generate_scenes(topic)
        scenes = result.get("scenes", [])
        print(f"\nЗапуск #{run+1}: {len(scenes)} сцен")

        prompts = [s["image_prompt"] for s in scenes]
        unique = len(set(prompts))

        print(f"  Уникальных промптов: {unique}/{len(prompts)}")

        if unique < len(prompts):
            print("  ⚠ ПОВТОРЫ:")
            for i, p in enumerate(prompts):
                count = prompts.count(p)
                if count > 1:
                    print(f"    Сцена {i}: {p[:80]}... (встречается {count}x)")
        else:
            print("  ✓ Все промпты уникальны")

        # Показываем первые 2 промпта
        print(f"\n  Примеры промптов:")
        for i, p in enumerate(prompts[:2]):
            print(f"    [{i}] {p[:120]}...")

if __name__ == "__main__":
    asyncio.run(main())
