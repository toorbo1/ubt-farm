"""
Модуль для наложения CTA (Call to Action) плашки в конце видео.
Показывает призыв перейти в Telegram-бот за бесплатным VPN.
"""
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    ImageClip,
    CompositeVideoClip,
    VideoFileClip,
)

from config.settings import settings


CTA_COLORS = {
    "bg": (30, 30, 40, 220),      # Полупрозрачный тёмный фон
    "border": (0, 200, 100, 255),  # Зелёная рамка
    "main_text": "#FFFFFF",
    "accent": "#00FF88",
    "arrow": "#00FF88",
}


class CTAOverlay:
    def __init__(self, font_path: Optional[Path] = None) -> None:
        self.width = settings.video_width
        self.height = settings.video_height
        self.bot_username = settings.telegram_bot_username
        self.cta_duration = settings.cta_duration

        font_candidates = [
            font_path,
            Path(settings.fonts_dir) / "arialbd.ttf",
            Path(settings.fonts_dir) / "Montserrat-Bold.ttf",
            Path("C:/Windows/Fonts/arialbd.ttf"),
            Path("C:/Windows/Fonts/impact.ttf"),
        ]

        self.font_title = None
        self.font_sub = None
        for fp in font_candidates:
            if fp and fp.exists():
                try:
                    self.font_title = ImageFont.truetype(str(fp), 64)
                    self.font_sub = ImageFont.truetype(str(fp), 48)
                    break
                except (IOError, OSError):
                    continue

        if self.font_title is None:
            self.font_title = ImageFont.load_default()
            self.font_sub = ImageFont.load_default()

    def create_cta_clip(
        self, video_duration: float
    ) -> ImageClip:
        """Создаёт CTA-плашку для последних N секунд видео."""
        start_time = max(0, video_duration - self.cta_duration)

        # 1. Затемнение всего кадра
        overlay = Image.new(
            "RGBA", (self.width, self.height), (0, 0, 0, 0)
        )
        draw = ImageDraw.Draw(overlay)

        # 2. Чёрная полупрозрачная подложка на весь кадр
        dark_overlay = Image.new(
            "RGBA", (self.width, self.height), (0, 0, 0, 160)
        )
        overlay = Image.alpha_composite(overlay, dark_overlay)
        draw = ImageDraw.Draw(overlay)

        # 3. Нижняя плашка с рамкой
        bar_h = 280
        bar_y = self.height - bar_h - 60
        bar_x1, bar_x2 = 60, self.width - 60

        # Рамка (закруглённая через прямоугольник)
        draw.rectangle(
            [bar_x1, bar_y, bar_x2, bar_y + bar_h],
            fill=CTA_COLORS["bg"],
            outline=CTA_COLORS["border"],
            width=4,
        )

        # 4. Текст: "🔒 Бесплатный VPN"
        title_text = "Бесплатный VPN"
        bbox = self.font_title.getbbox(title_text)
        tw = bbox[2] - bbox[0]
        title_x = (self.width - tw) // 2
        title_y = bar_y + 30
        draw.text((title_x, title_y), title_text, font=self.font_title, fill=CTA_COLORS["main_text"])

        # 5. Текст: @bot_username
        bot_text = f"@{self.bot_username}"
        bbox = self.font_sub.getbbox(bot_text)
        tw = bbox[2] - bbox[0]
        bot_x = (self.width - tw) // 2
        bot_y = bar_y + 120
        draw.text((bot_x, bot_y), bot_text, font=self.font_sub, fill=CTA_COLORS["accent"])

        # 6. Стрелка / указатель вниз (как призыв нажать)
        arrow_text = "👇 Нажми на ссылку в профиле"
        bbox = self.font_sub.getbbox(arrow_text)
        tw = bbox[2] - bbox[0]
        arrow_x = (self.width - tw) // 2
        arrow_y = bar_y + 200
        draw.text((arrow_x, arrow_y), arrow_text, font=self.font_sub, fill=CTA_COLORS["arrow"])

        clip = (
            ImageClip(np.array(overlay))
            .with_position(("center", "center"))
            .with_start(start_time)
            .with_duration(self.cta_duration)
        )

        return clip
