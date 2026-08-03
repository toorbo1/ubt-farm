"""
Базовый класс для загрузки видео на платформы.
Использует Playwright с поддержкой прокси и антидетект-профилей.
"""
import asyncio
import random
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from config.settings import settings


class BaseUploader(ABC):
    """Абстрактный класс загрузчика видео."""

    PLATFORM_NAME = "base"

    def __init__(self) -> None:
        self.headless = settings.upload_headless
        self.proxy = settings.upload_proxy
        self.profile_dir = Path(settings.upload_profile_dir)
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def __aenter__(self) -> "BaseUploader":
        await self.start()
        return self

    async def __aexit__(self, *args) -> None:
        await self.stop()

    async def start(self) -> None:
        """Запускает Playwright и браузер."""
        self._playwright = await async_playwright().start()

        launch_options = {
            "headless": self.headless,
        }
        if self.proxy:
            launch_options["proxy"] = {"server": self.proxy}

        self._browser = await self._playwright.chromium.launch(**launch_options)

        context_options = {
            "viewport": {"width": 1280, "height": 720},
            "locale": "ru-RU",
            "timezone_id": "Europe/Moscow",
        }

        self._context = await self._browser.new_context(**context_options)
        self._page = await self._context.new_page()

    async def stop(self) -> None:
        """Останавливает браузер."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    @abstractmethod
    async def login(self, **creds) -> None:
        """Авторизация на платформе."""
        ...

    @abstractmethod
    async def upload(self, video_path: Path, **metadata) -> bool:
        """Загружает видео на платформу."""
        ...

    async def human_delay(self, min_s: float = 0.5, max_s: float = 2.0) -> None:
        """Эмулирует задержку человека."""
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def human_scroll(self, count: int = 3) -> None:
        """Скроллит ленту как человек."""
        for _ in range(count):
            await self._page.evaluate(
                f"window.scrollBy(0, {random.randint(300, 700)})"
            )
            await self.human_delay(0.3, 1.5)

    async def human_type(self, text: str) -> None:
        """Печатает текст с переменной скоростью (эмуляция набора)."""
        for char in text:
            await self._page.keyboard.type(char, delay=random.randint(30, 120))
