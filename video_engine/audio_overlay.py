from pathlib import Path
from moviepy import AudioFileClip, CompositeAudioClip


def overlay_audio(
    video_path: Path, audio_path: Path, output_path: Path
) -> Path:
    """Накладывает аудио на видео (заменяет или смешивает с оригинальным звуком)."""
    from moviepy import VideoFileClip

    with VideoFileClip(str(video_path)) as video:
        with AudioFileClip(str(audio_path)) as audio:
            # Если аудио длиннее видео — обрезаем; если короче — зацикливаем
            if audio.duration > video.duration:
                audio = audio.subclipped(0, video.duration)
            elif audio.duration < video.duration:
                # Зацикливаем
                n_loops = int(video.duration / audio.duration) + 1
                audio = CompositeAudioClip([audio] * n_loops).with_duration(
                    video.duration
                )

            video = video.with_audio(audio)
            video.write_videofile(
                str(output_path),
                codec="libx264",
                audio_codec="aac",
                threads=4,
                logger=None,
            )

    return output_path
