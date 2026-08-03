"""
VPN Monitor — получение данных с сервера и хендлеры для inline-кнопок.
"""
import ssl
from datetime import datetime
from typing import Optional

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from config.settings import settings
from .keyboards import vpn_kb, vpn_servers_inline, main_kb

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


async def vpn_fetch_data() -> list[dict]:
    """Получает список серверов с /api/latest."""
    async with httpx.AsyncClient(verify=ssl_ctx, timeout=15.0) as client:
        resp = await client.get(
            f"{settings.vpn_api_url}/api/latest",
            headers={"X-API-Key": settings.vpn_api_key},
        )
        resp.raise_for_status()
        return resp.json()


async def vpn_server_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает детали конкретного сервера из inline-кнопки."""
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    if len(data) < 4:
        await query.edit_message_text("Ошибка.")
        return

    host = data[2]
    port = int(data[3])

    await query.edit_message_text(f"Загружаю историю для `{host}:{port}`...", parse_mode="Markdown")

    try:
        async with httpx.AsyncClient(verify=ssl_ctx, timeout=15.0) as client:
            # Текущий статус
            servers = await vpn_fetch_data()
            server_info = None
            for s in servers:
                if s.get("host") == host and s.get("port") == port:
                    server_info = s
                    break

            if not server_info:
                await query.edit_message_text(
                    f"Сервер `{host}:{port}` не найден.",
                    parse_mode="Markdown",
                )
                return

            # История
            hist_resp = await client.get(
                f"{settings.vpn_api_url}/api/history",
                params={"host": host, "port": port, "limit": 10},
                headers={"X-API-Key": settings.vpn_api_key},
            )
            hist_resp.raise_for_status()
            history = hist_resp.json()

        name = server_info.get("server_name", "N/A")
        ping = server_info.get("ping_ms")
        status = server_info.get("status", "offline")
        icon = "\U0001F7E2" if status == "online" else "\U0001F534"
        ping_str = f"{ping}ms" if ping is not None else "N/A"
        last_ts = server_info.get("last_ts", 0)
        last_str = datetime.fromtimestamp(last_ts).strftime("%Y-%m-%d %H:%M:%S") if isinstance(last_ts, (int, float)) and last_ts > 0 else str(last_ts)

        text = (
            f"📡 *{name}*\n\n"
            f"`{host}:{port}`\n"
            f"Статус: {icon} {status.upper()}\n"
            f"Пинг: {ping_str}\n"
            f"Последняя проверка: {last_str}\n\n"
            f"*Последние 10 проверок:*\n"
        )

        for h in history:
            h_icon = "\U0001F7E2" if h.get("status") == "online" else "\U0001F534"
            h_ping = h.get("ping_ms", "\u2014")
            h_ts = h.get("ts", 0)
            h_ts_str = datetime.fromtimestamp(h_ts).strftime("%H:%M") if isinstance(h_ts, (int, float)) else str(h_ts)
            text += f"{h_icon} {h_ping}ms ({h_ts_str})\n"

        await query.edit_message_text(text, parse_mode="Markdown")

    except Exception as e:
        await query.edit_message_text(f"Ошибка: `{e}`", parse_mode="Markdown")
