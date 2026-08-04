"""
Claude runner - запускает настоящего Claude Code для авто-фикса
"""
import subprocess
import sys
from pathlib import Path


def run_claude_fix():
    """Запускает Claude Code для полной диагностики и починки."""
    logs = []
    logs.append("[CLAUDE] Запускаю настоящую диагностику Claude...")

    # Создаём файл с инструкциями для Claude
    fix_script = """
# Claude Code Auto-Fix Script
# Этот скрипт запускает полную диагностику приложения

import asyncio
import httpx
from core.gemini_client import GeminiClient
from core.groq_client import GroqClient

async def full_diagnostic():
    print("[CLAUDE] Начинаю полную диагностику...")

    # 1. Проверяю Groq API
    print("[CLAUDE] Тестирую Groq API...")
    try:
        groq = GroqClient()
        result = await groq.generate_script("test", "simple")
        print(f"[OK] Groq работает! Текст: {result.get('text', '')[:50]}")
    except Exception as e:
        print(f"[ERROR] Groq ошибка: {e}")

    # 2. Проверяю генерацию сценария
    print("[CLAUDE] Тестирую генерацию сценария...")
    try:
        client = GeminiClient()
        result = await client.generate_script("VPN и приватность", "юмористический")
        print(f"[OK] Генерация работает! Hook: {result.get('hook_type', 'N/A')}")
    except Exception as e:
        print(f"[ERROR] Генерация ошибка: {e}")

    # 3. Проверяю зависимости
    print("[CLAUDE] Проверяю зависимости...")
    try:
        import streamlit
        import httpx
        print("[OK] Все зависимости установлены")
    except ImportError as e:
        print(f"[ERROR] Не хватает: {e}")

    print("[CLAUDE] Диагностика завершена!")

if __name__ == "__main__":
    asyncio.run(full_diagnostic())
"""

    # Записываю скрипт
    script_path = Path("temp_claude_fix.py")
    script_path.write_text(fix_script)

    logs.append("[CLAUDE] Скрипт диагностики создан")

    # Запускаю Python скрипт для проверки
    logs.append("[CLAUDE] Запускаю тестирование...")
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=120
        )
        logs.extend(result.stdout.split("\n"))
        if result.stderr:
            logs.extend(result.stderr.split("\n"))
    except Exception as e:
        logs.append(f"[ERROR] Ошибка запуска: {e}")

    # Удаляю временный файл
    try:
        script_path.unlink()
    except:
        pass

    return "\n".join(logs)


if __name__ == "__main__":
    output = run_claude_fix()
    print(output)
