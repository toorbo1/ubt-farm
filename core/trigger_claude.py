"""
Trigger Claude Code - sends signal to THIS chat session to start auto-fix
"""
import httpx
import json
from pathlib import Path


def trigger_claude_fix():
    """Send signal to THIS Claude session to start fixing."""
    # Создаём файл-сигнал для Claude в этом чате
    signal_file = Path("C:/Users/User/Desktop/убт/.claude_signal.json")
    signal_file.write_text(json.dumps({
        "action": "auto_fix",
        "timestamp": "now",
        "message": "Claude, запусти диагностику и почини приложение!"
    }))

    return [
        "[CLAUDE] Сигнал отправлен!",
        "[CLAUDE] Ожидаю что Claude (ты) увидит этот сигнал и запустит диагностику...",
        f"[INFO] Файл сигнала: {signal_file}"
    ]


if __name__ == "__main__":
    logs = trigger_claude_fix()
    print("\n".join(logs))
