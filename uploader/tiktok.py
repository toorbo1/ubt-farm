from pathlib import Path
from typing import Optional

from .base import BaseUploader


class TikTokUploader(BaseUploader):
    PLATFORM_NAME = "tiktok"

    async def login(
        self,
        cookies_file: Optional[Path] = None,
        **creds
    ) -> None:
        if cookies_file and cookies_file.exists():
            # Восстанавливаем сессию из кук
            cookies = []
            for line in cookies_file.read_text().splitlines():
                if "=" in line:
                    key, val = line.strip().split("=", 1)
                    cookies.append({
                        "name": key,
                        "value": val,
                        "domain": ".tiktok.com",
                        "path": "/",
                    })
            if cookies:
                await self._context.add_cookies(cookies)
                return

        # Либо открываем окно для ручного входа
        await self._page.goto("https://www.tiktok.com/login")
        print("[TikTok] Please log in manually in the browser window.")
        await self._page.wait_for_url(
            "https://www.tiktok.com/*", timeout=120000
        )

        # Сохраняем куки
        cookies = await self._context.cookies()
        if cookies_file:
            cookie_str = "\n".join(
                f"{c['name']}={c['value']}" for c in cookies
            )
            cookies_file.write_text(cookie_str)

        await self.human_delay(2, 4)

    async def upload(
        self,
        video_path: Path,
        description: str = "",
        hashtags: Optional[list[str]] = None,
        **metadata
    ) -> bool:
        try:
            await self._page.goto(
                "https://www.tiktok.com/upload", timeout=30000
            )
            await self.human_delay(2, 4)

            # Ищем input[type=file] и загружаем видео
            file_input = await self._page.query_selector(
                "input[type=file]"
            )
            if not file_input:
                # Пробуем альтернативный селектор
                file_input = await self._page.query_selector(
                    ".upload-btn-input"
                )
            if not file_input:
                raise RuntimeError("File input not found on TikTok upload page")

            await file_input.set_input_files(str(video_path))
            print("[TikTok] Video file selected, waiting for processing...")
            await self.human_delay(5, 10)

            # Описание
            caption = description
            if hashtags:
                caption += " " + " ".join(hashtags)

            caption_area = await self._page.query_selector(
                "div[contenteditable=true]"
            )
            if caption_area:
                await caption_area.click()
                await self.human_type(caption)

            await self.human_delay(1, 2)

            # Кнопка "Post"
            post_btn = await self._page.query_selector(
                "button[type=submit]"
            )
            if post_btn:
                await post_btn.click()
                print("[TikTok] Video posted!")
                return True

            raise RuntimeError("Post button not found")
        except Exception as e:
            print(f"[TikTok] Upload failed: {e}")
            return False
