from pathlib import Path
from typing import Optional

from .base import BaseUploader


class InstagramUploader(BaseUploader):
    PLATFORM_NAME = "instagram"

    async def login(
        self,
        cookies_file: Optional[Path] = None,
        **creds
    ) -> None:
        if cookies_file and cookies_file.exists():
            cookies = []
            for line in cookies_file.read_text().splitlines():
                if "=" in line:
                    key, val = line.strip().split("=", 1)
                    cookies.append({
                        "name": key,
                        "value": val,
                        "domain": ".instagram.com",
                        "path": "/",
                    })
            if cookies:
                await self._context.add_cookies(cookies)
                return

        await self._page.goto("https://www.instagram.com/accounts/login/")
        print("[Instagram] Please log in manually.")
        await self._page.wait_for_url(
            "https://www.instagram.com/*", timeout=120000
        )

        if cookies_file:
            cookies = await self._context.cookies()
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
                "https://www.instagram.com", timeout=30000
            )
            await self.human_delay(2, 4)

            # Кнопка "+" (Create)
            create_btn = await self._page.query_selector(
                "svg[aria-label='New post']"
            )
            if create_btn:
                await create_btn.click()
                await self.human_delay(1, 2)

            # File input для Reels
            file_input = await self._page.query_selector(
                "input[type=file]"
            )
            if file_input:
                await file_input.set_input_files(str(video_path))
                print("[Instagram] Video file selected...")
                await self.human_delay(3, 7)

            # Next / Crop
            next_btn = await self._page.query_selector(
                "div[role='button']:has-text('Next')"
            )
            if next_btn:
                await next_btn.click()
                await self.human_delay(1, 2)

            # Ещё раз Next (для Reels)
            next_btn2 = await self._page.query_selector(
                "div[role='button']:has-text('Next')"
            )
            if next_btn2:
                await next_btn2.click()
                await self.human_delay(1, 2)

            # Описание
            caption_area = await self._page.query_selector(
                "div[aria-label='Write a caption...']"
            )
            if caption_area:
                await caption_area.click()
                caption_text = description
                if hashtags:
                    caption_text += "\n\n" + " ".join(hashtags)
                await self.human_type(caption_text)
                await self.human_delay(1, 2)

            # Share
            share_btn = await self._page.query_selector(
                "div[role='button']:has-text('Share')"
            )
            if share_btn:
                await share_btn.click()
                print("[Instagram] Reel posted!")
                return True

            raise RuntimeError("Share button not found")
        except Exception as e:
            print(f"[Instagram] Upload failed: {e}")
            return False
