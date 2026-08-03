import random
from pathlib import Path
from typing import Optional

from config.settings import settings


VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}


class BackgroundSelector:
    """Выбирает и подготавливает случайное фоновое видео из библиотеки."""

    def __init__(self, backgrounds_dir: Optional[Path] = None) -> None:
        self.bg_dir = Path(backgrounds_dir or settings.backgrounds_dir)
        self.bg_dir.mkdir(parents=True, exist_ok=True)

    def scan_library(self) -> list[Path]:
        """Сканирует папку с фоновыми видео."""
        videos = [
            p for p in self.bg_dir.iterdir()
            if p.suffix.lower() in VIDEO_EXTENSIONS
        ]
        return videos

    def pick_random(self) -> Optional[Path]:
        """Выбирает случайное видео из библиотеки."""
        videos = self.scan_library()
        if not videos:
            return None
        return random.choice(videos)

    def pick_by_tags(self, tags: list[str]) -> Optional[Path]:
        """Выбирает случайное видео, чьё имя содержит хотя бы один из тегов."""
        videos = self.scan_library()
        candidates = [
            v for v in videos
            if any(tag.lower() in v.stem.lower() for tag in tags)
        ]
        if not candidates:
            return self.pick_random()
        return random.choice(candidates)

    def add_video(self, source_path: Path) -> Path:
        """Копирует видео в библиотеку."""
        dest = self.bg_dir / source_path.name
        if not dest.exists():
            dest.write_bytes(source_path.read_bytes())
        return dest
