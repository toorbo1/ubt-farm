"""
Генерация динамических пословных субтитров в стиле Alex Hormozi.
Каждый чанк (1-2 слова) рендерится как отдельный ImageClip с помощью Pillow.
Ключевые слова подсвечиваются жёлтым (#FFD700).
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
from core.subtitle_timing import SubtitleTrack, WordTiming


FONT_COLOR = "#FFFFFF"
HIGHLIGHT_COLOR = "#FFD700"
SHADOW_COLOR = "#000000"
STROKE_COLOR = "#000000"


class SubtitleRenderer:
    def __init__(self, font_path: Optional[Path] = None) -> None:
        self.font_size = settings.subtitle_font_size
        self.width = settings.video_width
        self.height = settings.video_height

        # Ищем жирный шрифт
        font_candidates = [
            font_path,
            Path(settings.fonts_dir) / "arialbd.ttf",
            Path(settings.fonts_dir) / "Montserrat-Bold.ttf",
            Path(settings.fonts_dir) / "Roboto-Bold.ttf",
            Path("C:/Windows/Fonts/arialbd.ttf"),
            Path("C:/Windows/Fonts/impact.ttf"),
        ]

        self.font = None
        for fp in font_candidates:
            if fp and fp.exists():
                try:
                    self.font = ImageFont.truetype(str(fp), self.font_size)
                    break
                except (IOError, OSError):
                    continue

        if self.font is None:
            self.font = ImageFont.load_default()

    def render_track(
        self, track: SubtitleTrack, output_path: Optional[Path] = None
    ) -> list[ImageClip]:
        """Создаёт список ImageClip для каждого слова/чанка."""
        clips: list[ImageClip] = []

        for wt in track.word_timings:
            clip = self._render_word_clip(wt)
            clips.append(clip)

        return clips

    def _render_word_clip(self, wt: WordTiming) -> ImageClip:
        """Рендерит одно слово/группу слов как ImageClip."""
        color = HIGHLIGHT_COLOR if wt.is_highlight else FONT_COLOR
        img = self._render_text(wt.word, color)

        clip = (
            ImageClip(img)
            .with_position(("center", "center"))
            .with_start(wt.start)
            .with_duration(wt.duration)
            .with_opacity(1.0)
        )
        return clip

    def _render_text(self, text: str, color: str) -> np.ndarray:
        """Рендерит текст на прозрачном фоне через Pillow, возвращает numpy array."""
        # Сначала измеряем размер текста
        bbox = self.font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        pad_x = 40
        pad_y = 20
        img_w = tw + pad_x * 2
        img_h = th + pad_y * 2

        # Альфа-слой (RGBA)
        img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Тень (смещение на 3px)
        shadow_offset = 4
        draw.text(
            (pad_x + shadow_offset, pad_y + shadow_offset),
            text,
            font=self.font,
            fill=(0, 0, 0, 180),
        )

        # Обводка (рисуем текст 4 раза со смещением)
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text(
                (pad_x + dx, pad_y + dy),
                text,
                font=self.font,
                fill=(0, 0, 0, 200),
            )

        # Основной текст
        draw.text(
            (pad_x, pad_y),
            text,
            font=self.font,
            fill=color,
        )

        return np.array(img)

    @staticmethod
    def animate_subtitle(clip: ImageClip) -> ImageClip:
        """Добавляет микро-анимацию: появление с небольшим скейлом."""
        def make_frame(t):
            # Простой fade-in + scale
            duration = clip.duration
            if duration <= 0:
                return clip.get_frame(0)

            progress = min(t / 0.15, 1.0) if t < 0.15 else 1.0
            return clip.get_frame(t * progress)

        return clip
