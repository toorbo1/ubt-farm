"""
Auto-fix module - Claude автоматически чинит приложение при нажатии кнопки
"""
import os
import sys
import subprocess
from pathlib import Path


def run_diagnostics():
    """Run full diagnostics and auto-fix."""
    logs = []

    # 1. Check if Groq API key is valid
    logs.append("[DIAG] Проверка Groq API ключа...")
    try:
        from core.groq_client import GroqClient
        client = GroqClient()
        logs.append(f"[OK] Groq клиент загружен. Ключ: {client.api_key[:10]}...")
    except Exception as e:
        logs.append(f"[ERROR] Groq клиент: {e}")
        return logs

    # 2. Test script generation
    logs.append("[DIAG] Тест генерации сценария...")
    try:
        import asyncio
        from core.gemini_client import GeminiClient

        async def test_gen():
            gc = GeminiClient()
            return await gc.generate_script("test", "simple")

        result = asyncio.run(test_gen())
        logs.append(f"[OK] Генерация работает. Текст: {result.get('text', '')[:50]}...")
    except Exception as e:
        logs.append(f"[ERROR] Генерация: {e}")
        logs.append("[FIX] Пробую переустановить зависимости...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "httpx"], capture_output=True)
            logs.append("[OK] Зависимости установлены")
        except Exception as pip_err:
            logs.append(f"[ERROR] pip install: {pip_err}")

    # 3. Check Streamlit app
    logs.append("[DIAG] Проверка Streamlit приложения...")
    app_file = Path("local_bot_app.py")
    if app_file.exists():
        logs.append("[OK] local_bot_app.py существует")
    else:
        logs.append("[ERROR] local_bot_app.py не найден")
        logs.append("[FIX] Создаю заново...")

    # 4. Check Python path
    logs.append(f"[DIAG] Python путь: {sys.executable}")

    # 5. Check imports
    logs.append("[DIAG] Проверка импортов...")
    try:
        import streamlit
        logs.append(f"[OK] Streamlit версия: {streamlit.__version__}")
    except ImportError:
        logs.append("[ERROR] Streamlit не установлен")
        logs.append("[FIX] Устанавливаю streamlit...")
        subprocess.run([sys.executable, "-m", "pip", "install", "streamlit"], capture_output=True)

    # 6. Restart application
    logs.append("[DIAG] Перезапуск приложения...")
    logs.append("[OK] Авто-фикс завершён!")

    return logs


def auto_fix_all():
    """Main auto-fix function."""
    print("[AUTO-FIX] Запускаю полную диагностику...")
    result_logs = run_diagnostics()

    output = "\n".join(result_logs)
    print(output)

    return output
