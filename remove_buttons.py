#!/usr/bin/env python3
"""
Скрипт для удаления кнопок "VPN монитор" и "Ферма видео" из проекта убт
"""
import re
from pathlib import Path

def remove_functions_from_handlers(file_path: Path):
    """Удаляет функции связанные с VPN и Фермой видео"""
    content = file_path.read_text(encoding='utf-8')

    # Паттерны для удаления функций
    patterns_to_remove = [
        r'async def handle_farm_text\(.*?\n(?=async def|\n# ===)',  # вся функция до следующей async def или комментария
        r'async def custom_text_received\(.*?\n(?=async def|\n\nasync def)',
        r'async def list_videos\(.*?\n(?=async def|\n\nasync def)',
        r'async def farm_status\(.*?\n(?=async def|\n\n# ===)',
        r'async def show_vpn\(.*?\n(?=async def|\n\nasync def)',
        r'async def _fetch_and_show_vpn\(.*?\n(?=async def|\n\nasync def)',
        r'async def handle_vpn_text\(.*?\n(?=async def|\n\nasync def)',
        r'async def _show_vpn_stats\(.*?\n(?=async def|\n\n# ===)',
    ]

    for pattern in patterns_to_remove:
        content = re.sub(pattern, '', content, flags=re.DOTALL | re.MULTILINE)

    # Удаляем проверку секций FARM и VPN
    section_check_pattern = r'''    # ─── Раздел: Ферма видео ───
    if section == S_FARM:
        await handle_farm_text\(update, context, text\)
        return

    # ─── Раздел: Модели ───
    if section == S_MODELS:
        await handle_models_text\(update, context, text\)
        return

    # ─── Раздел: VPN ───
    if section == S_VPN:
        await handle_vpn_text\(update, context, text\)
        return'''

    content = re.sub(section_check_pattern, '''    # ─── Раздел: Модели ───
    if section == S_MODELS:
        await handle_models_text(update, context, text)
        return''', content)

    file_path.write_text(content, encoding='utf-8')
    print(f"[OK] Removed functions from {file_path.name}")

def update_keyboards(file_path: Path):
    """Updates keyboards.py removing farm_kb and vpn_kb"""
    content = file_path.read_text(encoding='utf-8')

    # Remove farm_kb and vpn_kb functions
    content = re.sub(r'\ndef farm_kb\(\).*?return ReplyKeyboardMarkup\(kb, resize_keyboard=True\)', '', content, flags=re.DOTALL)
    content = re.sub(r'\ndef vpn_kb\(\).*?return ReplyKeyboardMarkup\(kb, resize_keyboard=True\)', '', content, flags=re.DOTALL)

    file_path.write_text(content, encoding='utf-8')
    print(f"[OK] Updated keyboards in {file_path.name}")

if __name__ == '__main__':
    project_root = Path(r'C:\Users\User\Desktop\убт')
    handlers_file = project_root / 'bot' / 'handlers.py'
    keyboards_file = project_root / 'bot' / 'keyboards.py'

    if handlers_file.exists():
        remove_functions_from_handlers(handlers_file)
    else:
        print(f"[ERROR] File not found: {handlers_file}")

    if keyboards_file.exists():
        update_keyboards(keyboards_file)
    else:
        print(f"[ERROR] File not found: {keyboards_file}")

    print("\n[DONE] Ready to commit changes and deploy!")
