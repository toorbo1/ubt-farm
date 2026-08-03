"""
Микро-трансформации для уникализации видео.
Комбинирует несколько незаметных изменений, чтобы
изменить хеш/отпечаток видео для anti-duplicate систем.
"""
import random
from pathlib import Path
import subprocess


def apply_micro_transforms(input_path: Path, output_path: Path) -> Path:
    """
    Применяет набор микро-изменений к видео через ffmpeg:
    - Удаление метаданных
    - Микро-сдвиг временной шкалы (1-2 кадра)
    - Изменение уровня громкости на ±0.5dB
    - Микро-изменение контраста/яркости
    """
    # Параметры
    # brightness: -0.02..+0.02, contrast: 0.98..1.02
    brightness = random.uniform(-0.02, 0.02)
    contrast = random.uniform(0.98, 1.02)
    volume = random.uniform(0.97, 1.03)  # тише/громче на 3%
    hue = random.uniform(-5, 5)           # сдвиг оттенка

    # Случайный seek на 1-2 кадра (сдвиг временной шкалы)
    frame_shift = random.uniform(0, 0.067)  # до 2 кадров при 30fps

    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(frame_shift),
        "-i", str(input_path),
        "-map_metadata", "-1",
        "-vf",
        (
            f"eq=brightness={brightness}:contrast={contrast},"
            f"hue=h={hue}"
        ),
        "-af", f"volume={volume}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(output_path),
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Micro-transform failed:\n{result.stderr}"
        )
    return output_path
