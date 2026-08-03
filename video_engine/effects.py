"""
Эффекты для визуальной обработки: цветокоррекция, микро-зум, изменение скорости.
Без использования OpenCV (чистый numpy + MoviePy).
"""
import random
import numpy as np
from moviepy import VideoFileClip, VideoClip


def apply_micro_zoom(clip: VideoFileClip) -> VideoFileClip:
    """
    Микро-зум: медленно приближает кадр на 1-3% на протяжении видео.
    Незаметно для зрителя, но меняет пиксельную структуру.
    """
    zoom_factor = 0.97 + random.random() * 0.03  # 0.97..1.00

    def zoom_effect(get_frame, t):
        frame = get_frame(t)
        h, w = frame.shape[:2]
        new_w = int(w * zoom_factor)
        new_h = int(h * zoom_factor)
        x_off = (w - new_w) // 2
        y_off = (h - new_h) // 2
        return frame[y_off:y_off+new_h, x_off:x_off+new_w]

    return clip.transform(zoom_effect)


def apply_speed_tweak(clip: VideoFileClip) -> VideoFileClip:
    """
    Изменяет скорость видео на 1-2% (рандомно замедляет или ускоряет).
    Меняет FPS-структуру, что усложняет детект копии.
    """
    speed = 0.98 + random.random() * 0.04  # 0.98..1.02
    return clip.with_duration(clip.duration / speed).with_fps(clip.fps)


def apply_color_tweak(clip: VideoFileClip) -> VideoFileClip:
    """
    Невидимая цветокоррекция: минимальное смещение гаммы/RGB.
    """
    r_shift = 1.0 + random.uniform(-0.02, 0.02)
    g_shift = 1.0 + random.uniform(-0.02, 0.02)
    b_shift = 1.0 + random.uniform(-0.02, 0.02)

    def color_transform(get_frame, t):
        frame = get_frame(t).astype(np.float32)
        frame[:, :, 0] = np.clip(frame[:, :, 0] * r_shift, 0, 255)
        frame[:, :, 1] = np.clip(frame[:, :, 1] * g_shift, 0, 255)
        frame[:, :, 2] = np.clip(frame[:, :, 2] * b_shift, 0, 255)
        return frame.astype(np.uint8)

    return clip.transform(color_transform)


def maybe_mirror_background(clip: VideoFileClip) -> VideoFileClip:
    """С вероятностью 50% отражает видео по горизонтали."""
    if random.random() < 0.5:
        return clip.image_transform(lambda img: img[:, ::-1])
    return clip
