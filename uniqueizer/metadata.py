"""
Очистка метаданных и EXIF из видеофайлов.
Использует ffmpeg для полного удаления всех метаданных.
"""
import subprocess
from pathlib import Path


def strip_exif(input_path: Path, output_path: Path) -> Path:
    """
    Удаляет все метаданные из видео через ffmpeg:
    - EXIF
    - XMP
    - Дата/время создания
    - Информация о камере/кодеке
    - Все private-теги
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-map_metadata", "-1",     # Удалить всю метаданные
        "-map_chapters", "-1",     # Удалить главы
        "-fflags", "+bitexact",    # Флаг для чистого выхода
        "-flags:v", "+bitexact",   # Поток видео без случайных флагов
        "-flags:a", "+bitexact",   # Поток аудио без случайных флагов
        "-codec", "copy",          # Не перекодировать (быстро)
        str(output_path),
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg metadata strip failed:\n{result.stderr}"
        )
    return output_path


def rewrite_metadata_with_random(input_path: Path, output_path: Path) -> Path:
    """
    Перезаписывает метаданные случайными значениями
    вместо полного удаления (более естественно для алгоритмов).
    """
    import random
    from datetime import datetime, timedelta

    fake_date = datetime.now() - timedelta(
        days=random.randint(1, 365),
        hours=random.randint(0, 23),
    )
    fake_date_str = fake_date.strftime("%Y-%m-%dT%H:%M:%S.000000Z")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-map_metadata", "-1",
        "-metadata", f"creation_time={fake_date_str}",
        "-metadata", f"handler_name=",
        "-metadata", "encoder=",
        "-codec", "copy",
        str(output_path),
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg metadata rewrite failed:\n{result.stderr}"
        )
    return output_path
