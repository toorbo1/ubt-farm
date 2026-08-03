from pathlib import Path
from typing import Optional

from .base import BaseUploader


class YouTubeUploader(BaseUploader):
    PLATFORM_NAME = "youtube"

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
                        "domain": ".youtube.com",
                        "path": "/",
                    })
            if cookies:
                await self._context.add_cookies(cookies)
                return

        await self._page.goto("https://accounts.google.com/signin")
        print("[YouTube] Please log in to Google/YouTube manually.")
        await self._page.wait_for_url(
            "https://www.youtube.com/*", timeout=120000
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
        title: str = "",
        description: str = "",
        hashtags: Optional[list[str]] = None,
        **metadata
    ) -> bool:
        try:
            await self._page.goto(
                "https://studio.youtube.com", timeout=30000
            )
            await self.human_delay(3, 5)

            # Кнопка "Create" / "Upload"
            create_btn = await self._page.query_selector(
                "ytcp-button#create-icon"
            )
            if not create_btn:
                create_btn = await self._page.query_selector(
                    "ytcp-button[aria-label='Create']"
                )
            if create_btn:
                await create_btn.click()
                await self.human_delay(1, 2)

            upload_btn = await self._page.query_selector(
                "ytcp-menu-item:has-text('Upload videos')"
            )
            if not upload_btn:
                upload_btn = await self._page.query_selector("text=Upload videos")
            if upload_btn:
                await upload_btn.click()
                await self.human_delay(1, 2)

            # File input
            file_input = await self._page.query_selector(
                "input[type=file]"
            )
            if file_input:
                await file_input.set_input_files(str(video_path))
                print("[YouTube] Video file selected, processing...")
                await self.human_delay(5, 15)

            # Title
            title_input = await self._page.query_selector(
                "ytcp-video-title-field #textbox"
            )
            if title_input:
                await title_input.click()
                await title_input.fill("")
                await self.human_type(title or "Shorts video")
                await self.human_delay(1, 2)

            # Description
            desc_input = await self._page.query_selector(
                "ytcp-video-description-field #textbox"
            )
            if desc_input:
                desc_text = description
                if hashtags:
                    desc_text += "\n\n" + " ".join(hashtags)
                await desc_input.click()
                await desc_input.fill("")
                await self.human_type(desc_text)
                await self.human_delay(1, 2)

            # Публикация
            next_btn = await self._page.query_selector(
                "ytcp-button:has-text('Next')"
            )
            for _ in range(3):
                if next_btn:
                    await next_btn.click()
                    await self.human_delay(1, 2)
                else:
                    break

            # Public
            public_radio = await self._page.query_selector(
                "tp-yt-paper-radio-button:has-text('Public')"
            )
            if public_radio:
                await public_radio.click()
                await self.human_delay(1, 2)

            publish_btn = await self._page.query_selector(
                "ytcp-button:has-text('Publish')"
            )
            if publish_btn:
                await publish_btn.click()
                print("[YouTube] Video published!")
                return True

            raise RuntimeError("Publish button not found")
        except Exception as e:
            print(f"[YouTube] Upload failed: {e}")
            return False
