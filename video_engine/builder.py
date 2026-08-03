"""
VideoBuilder — the three-AI pipeline and the ffmpeg assembly.

The pipeline is audio-first. TTS runs before anything visual, so every
duration downstream — clip length, crossfade offset, subtitle timing, the
moment the CTA appears — comes from what was actually spoken. The previous
order (LLM guesses `duration`, video is cut to it, audio is stretched to fit
afterwards) drifted by a second or more by the end of a 20-second clip, which
is exactly where the call to action sits.

Assembly is three ffmpeg passes rather than one:
  1. the visual timeline (xfade chain between scene clips)
  2. the narration (concat + loudnorm to the platform target)
  3. the mux (burn subtitles, overlay the CTA, attach audio)
Splitting them keeps each filter graph small enough to debug, and a failure
names the stage it happened in.
"""
from __future__ import annotations

import secrets
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, List, Optional

from config.settings import settings
from core.ffmpeg_utils import (
    _encoder_args,
    escape_filter_path,
    run_ffmpeg,
)
from core.image_gen import get_image_generator
from core.llm_client import LLMClient
from core.subtitle_timing import SubtitleTimingGenerator, render_ass
from core.tts_client import SpeechChunk, SpokenWord, TTSClient
from core.video_ai import get_img2video_generator

ProgressFn = Optional[Callable[[str], Awaitable[None]]]

# Soft transitions only. Hard wipes draw the eye to the cut, which on
# generated footage reads as a glitch rather than as editing.
XFADE_TRANSITIONS: tuple[str, ...] = (
    "fade",
    "smoothleft",
    "fadeblack",
    "smoothup",
    "circleopen",
    "smoothright",
)


@dataclass
class BuiltScene:
    """One scene, accumulating artefacts as it moves through the pipeline."""

    index: int
    narration: str
    image_prompt: str
    speech: SpeechChunk
    image_path: Optional[Path] = None
    clip_path: Optional[Path] = None

    @property
    def duration(self) -> float:
        """Narration plus its trailing pause — the scene's slot in the timeline."""
        return self.speech.duration


class VideoBuilder:
    def __init__(self, video_provider: Optional[str] = None) -> None:
        self.llm = LLMClient()
        self.tts = TTSClient()
        self.image_gen = get_image_generator()
        self.video_provider = video_provider
        self.img2video = get_img2video_generator(prefer=video_provider)
        self.subtitle_timing = SubtitleTimingGenerator()
        self.output_dir = Path(settings.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scenes_dir = self.output_dir / "scenes"
        self.scenes_dir.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────── orchestration ───────────────────────────

    async def build(
        self,
        topic: Optional[str] = None,
        custom_script: Optional[str] = None,
        background_path: Optional[Path] = None,
        progress_callback: ProgressFn = None,
    ) -> Path:
        self.reset_workspace()
        scenes, highlight_words = await self._script(topic, custom_script,
                                                     progress_callback)
        built = await self.synthesize_scenes(scenes, progress_callback)
        await self.generate_images(built, progress_callback)
        await self.generate_clips(built, progress_callback)
        return await self.assemble(built, highlight_words, progress_callback)

    async def build_batch(
        self,
        count: int,
        topics: Optional[List[str]] = None,
        progress_callback: ProgressFn = None,
    ) -> List[Path]:
        paths: List[Path] = []
        for i in range(count):
            topic = topics[i % len(topics)] if topics else None
            paths.append(await self.build(topic=topic,
                                          progress_callback=progress_callback))
        return paths

    def reset_workspace(self) -> None:
        """Drop cached scene artefacts so a run never reuses a previous take."""
        if self.scenes_dir.exists():
            shutil.rmtree(self.scenes_dir, ignore_errors=True)
        self.scenes_dir.mkdir(parents=True, exist_ok=True)

    async def cleanup(self) -> None:
        await self.llm.close()

    # ─────────────────────────── stages ───────────────────────────

    async def _script(
        self, topic: Optional[str], custom_script: Optional[str], log: ProgressFn
    ) -> tuple[List[dict], List[str]]:
        if custom_script:
            return self._text_to_fallback_scenes(custom_script), []
        data = await self.llm.generate_scenes(topic)
        scenes = data.get("scenes", [])
        if not scenes:
            raise RuntimeError("AI #1 вернул пустой сценарий")
        await self._emit(log, f"[OK] AI#1 Сценарий готов ({len(scenes)} сцен)")
        return scenes, data.get("highlight_words", [])

    async def synthesize_scenes(
        self, scenes: List[dict], log: ProgressFn = None
    ) -> List[BuiltScene]:
        """Render every scene's narration. This is what sets the timeline."""
        built: List[BuiltScene] = []
        for i, scene in enumerate(scenes):
            narration = str(scene.get("narration", "")).strip()
            chunk = await self.tts.synthesize_scene(
                narration, self.scenes_dir / f"scene_{i:02d}.wav"
            )
            built.append(BuiltScene(
                index=i,
                narration=narration,
                image_prompt=str(scene.get("image_prompt") or narration),
                speech=chunk,
            ))
            note = " (тишина — TTS недоступен)" if chunk.synthetic else ""
            await self._emit(
                log,
                f"[OK] Озвучка {i + 1}/{len(scenes)}: {chunk.duration:.1f}с{note}",
            )
        if not built:
            raise RuntimeError("нет ни одной сцены для озвучки")
        return built

    async def generate_images(
        self, built: List[BuiltScene], log: ProgressFn = None
    ) -> List[BuiltScene]:
        # A fresh per-run seed base: without it a provider happily returns the
        # same cached frame for the same prompt on every run of a topic.
        run_seed = secrets.randbelow(2 ** 31)
        for scene in built:
            path = self.scenes_dir / f"scene_{scene.index:02d}.jpg"
            seed = (run_seed + scene.index * 104729) % (2 ** 31)
            try:
                await self.image_gen.generate(scene.image_prompt, path, seed=seed)
                await self._emit(
                    log, f"[OK] AI#2 Картинка {scene.index + 1}/{len(built)}")
            except Exception as e:
                await self._emit(
                    log, f"[!] AI#2 Картинка {scene.index + 1} — запасная: {e}")
                path = await self._generate_fallback_image(
                    scene.narration, path, seed)
            scene.image_path = path
        return built

    async def generate_clips(
        self, built: List[BuiltScene], log: ProgressFn = None
    ) -> List[BuiltScene]:
        overlap = self.transition_duration(built)
        for scene in built:
            # Every clip but the first carries `overlap` extra seconds of
            # footage. That tail is what the crossfade out of the previous
            # scene consumes, so the finished timeline still totals exactly
            # the narration length.
            length = scene.duration + (overlap if scene.index > 0 else 0.0)
            clip = self.scenes_dir / f"scene_video_{scene.index:02d}.mp4"
            try:
                await self.img2video.generate(
                    scene.image_path,
                    scene.image_prompt,
                    clip,
                    length,
                    index=scene.index,
                )
                await self._emit(
                    log, f"[OK] AI#3 Видео {scene.index + 1}/{len(built)}")
            except Exception as e:
                await self._emit(
                    log, f"[!] AI#3 Сцена {scene.index + 1} — статикой: {e}")
                clip = await self._still_clip(scene.image_path, length, clip)
            scene.clip_path = clip
        return built

    async def assemble(
        self,
        built: List[BuiltScene],
        highlight_words: Optional[List[str]] = None,
        log: ProgressFn = None,
        output_path: Optional[Path] = None,
    ) -> Path:
        overlap = self.transition_duration(built)
        total = sum(scene.duration for scene in built)
        output_path = output_path or (
            self.output_dir / f"ubt_video_{self._timestamp()}.mp4"
        )

        await self._emit(log, "[OK] Сборка 1/3: видеоряд...")
        timeline = await self._concat_video(built, overlap)

        await self._emit(log, "[OK] Сборка 2/3: звук...")
        narration = await self._concat_audio(built)

        ass_path = self._write_subtitles(built, total, highlight_words)
        cta_path = self._generate_cta_image()

        await self._emit(log, "[OK] Сборка 3/3: финальный проход...")
        await self._mux(timeline, narration, ass_path, cta_path,
                        output_path, total)

        await self._emit(
            log, f"[OK] Готово: {output_path.name} ({total:.1f}с)")
        return output_path

    # ─────────────────────────── assembly internals ───────────────────────

    @staticmethod
    def transition_duration(built: List[BuiltScene]) -> float:
        """Crossfade overlap, clamped so it can never swallow a whole scene."""
        if not settings.transitions_enabled or len(built) < 2:
            return 0.0
        shortest = min(scene.duration for scene in built)
        return max(0.0, min(settings.transition_duration, shortest / 2))

    async def _concat_video(self, built: List[BuiltScene], overlap: float) -> Path:
        clips = [scene.clip_path for scene in built]
        if len(clips) == 1:
            return clips[0]

        dst = self.scenes_dir / "timeline.mp4"

        if overlap <= 0:
            # Clips already share codec, size and fps, so a stream copy avoids
            # a second generation of encoding loss.
            listing = self.scenes_dir / "concat.txt"
            listing.write_text("\n".join(f"file '{c.name}'" for c in clips),
                               encoding="utf-8")
            await run_ffmpeg([
                "-f", "concat", "-safe", "0", "-i", str(listing),
                "-c", "copy",
                "-y", str(dst),
            ], timeout=900)
            return dst

        # xfade chain. `offset` is the absolute time the crossfade into clip k
        # begins: the end of scene k-1's narration minus the overlap, so the
        # transition plays over the trailing pause instead of over speech.
        inputs: List[str] = []
        for clip in clips:
            inputs += ["-i", str(clip)]

        steps: List[str] = []
        prev = "[0:v]"
        elapsed = built[0].duration
        for k in range(1, len(clips)):
            transition = XFADE_TRANSITIONS[(k - 1) % len(XFADE_TRANSITIONS)]
            label = f"[vx{k}]"
            steps.append(
                f"{prev}[{k}:v]xfade=transition={transition}"
                f":duration={overlap:.3f}:offset={elapsed - overlap:.3f}{label}"
            )
            prev = label
            elapsed += built[k].duration

        await run_ffmpeg([
            *inputs,
            "-filter_complex", ";".join(steps),
            "-map", prev,
            "-an",
            *_encoder_args(settings.video_crf, settings.video_preset),
            "-r", str(settings.video_fps),
            "-y", str(dst),
        ], timeout=1800)
        return dst

    async def _concat_audio(self, built: List[BuiltScene]) -> Path:
        """Join the per-scene wavs and normalise the result.

        loudnorm rather than a fixed gain: TikTok and YouTube normalise on
        upload, and material that arrives quiet gets lifted along with its
        noise floor. -14 LUFS is what both target.
        """
        dst = self.scenes_dir / "narration.wav"
        inputs: List[str] = []
        for scene in built:
            inputs += ["-i", str(scene.speech.audio_path)]
        labels = "".join(f"[{i}:a]" for i in range(len(built)))

        await run_ffmpeg([
            *inputs,
            "-filter_complex",
            f"{labels}concat=n={len(built)}:v=0:a=1[cat];"
            f"[cat]loudnorm=I={settings.loudness_lufs}:TP=-1.5:LRA=11,"
            f"aresample=48000[a]",
            "-map", "[a]",
            "-c:a", "pcm_s16le",
            "-y", str(dst),
        ], timeout=900)
        return dst

    def _write_subtitles(
        self,
        built: List[BuiltScene],
        total: float,
        highlight_words: Optional[List[str]],
    ) -> Path:
        """Shift each scene's TTS word boundaries onto the global timeline."""
        words: List[SpokenWord] = []
        offset = 0.0
        for scene in built:
            for word in scene.speech.words:
                words.append(SpokenWord(
                    text=word.text,
                    start=word.start + offset,
                    duration=word.duration,
                ))
            offset += scene.duration

        track = self.subtitle_timing.from_speech(
            words, total, highlight_words or [])
        path = self.scenes_dir / "subtitles.ass"
        path.write_text(render_ass(track.word_timings, total), encoding="utf-8")
        return path

    async def _mux(
        self,
        video: Path,
        audio: Path,
        ass_path: Path,
        cta_path: Path,
        output_path: Path,
        total: float,
    ) -> None:
        cta_start = max(0.0, total - settings.cta_duration)
        await run_ffmpeg([
            "-i", str(video),
            "-i", str(audio),
            # -loop so the still CTA has frames for the whole clip; its own
            # timeline then advances in lockstep with the output, which is what
            # makes the fade `st=` below line up with `enable=`.
            "-loop", "1", "-i", str(cta_path),
            "-filter_complex",
            f"[0:v]ass='{escape_filter_path(ass_path)}'[vs];"
            f"[2:v]format=rgba,fade=t=in:st={cta_start:.3f}:d=0.4:alpha=1[cta];"
            f"[vs][cta]overlay=0:0:enable='gte(t,{cta_start:.3f})'[v]",
            "-map", "[v]",
            "-map", "1:a",
            "-t", f"{total:.3f}",
            *_encoder_args(settings.video_crf, settings.video_preset),
            "-r", str(settings.video_fps),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart",
            "-y", str(output_path),
        ], timeout=1800)

    # ─────────────────────────── fallbacks & assets ───────────────────────

    async def _generate_fallback_image(
        self, text: str, output_path: Path, seed: Optional[int] = None
    ) -> Path:
        from core.image_gen import LocalFallbackGenerator
        return await LocalFallbackGenerator().generate(text, output_path, seed)

    async def _still_clip(
        self, image_path: Path, duration: float, output_path: Path
    ) -> Path:
        """Motionless clip — only reachable if even the local engine dies."""
        W, H = settings.video_width, settings.video_height
        await run_ffmpeg([
            "-loop", "1",
            "-framerate", str(settings.video_fps),
            "-t", f"{duration:.3f}",
            "-i", str(image_path),
            "-vf", (f"scale={W}:{H}:force_original_aspect_ratio=increase"
                    f":flags=lanczos,crop={W}:{H},setsar=1,format=yuv420p"),
            "-an",
            *_encoder_args(settings.video_crf, settings.video_preset),
            "-r", str(settings.video_fps),
            "-y", str(output_path),
        ], timeout=600)
        return output_path

    def _generate_cta_image(self) -> Path:
        """Full-frame RGBA overlay: gradient scrim, play button, prompt."""
        from PIL import Image, ImageDraw, ImageFont

        w, h = settings.video_width, settings.video_height
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        for y in range(h - 300, h):
            alpha = int(180 * (1 - (y - (h - 300)) / 300))
            draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

        cx, cy, r = w // 2, h - 180, 70
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 215, 0, 220))
        draw.polygon([(cx - 15, cy - 20), (cx - 15, cy + 20), (cx + 25, cy)],
                     fill=(0, 0, 0, 220))

        try:
            font = ImageFont.truetype("arialbd.ttf", 48)
        except Exception:
            font = ImageFont.load_default()
        draw.text((w // 2, h - 100), "Подпишись!",
                  fill=(255, 255, 255, 220), font=font, anchor="mt")

        cta_path = self.scenes_dir / "cta_overlay.png"
        img.save(cta_path)
        return cta_path

    # ─────────────────────────── helpers ───────────────────────────

    @staticmethod
    async def _emit(log: ProgressFn, message: str) -> None:
        print(message)
        if log:
            try:
                await log(message)
            except Exception:
                pass

    @staticmethod
    def _text_to_fallback_scenes(text: str) -> List[dict]:
        words = text.split()
        chunk_size = max(3, len(words) // 4)
        scenes = []
        for i in range(0, len(words), chunk_size):
            scenes.append({
                "narration": " ".join(words[i:i + chunk_size]),
                "image_prompt": ("abstract technology background, 9:16, "
                                 "cinematic lighting"),
            })
        return scenes

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:21]
