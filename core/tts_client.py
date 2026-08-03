"""
Text-to-speech with real word-level timing.

The pipeline is audio-first: a scene lasts exactly as long as its narration,
so every duration downstream (clip length, transition offset, subtitle timing)
comes from what was actually spoken rather than from a number the LLM guessed.

edge-tts reports WordBoundary events in 100-ns ticks, which is what makes
frame-accurate karaoke subtitles possible without a forced aligner.
"""
from __future__ import annotations

import asyncio
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config.settings import settings
from core.ffmpeg_utils import run_ffmpeg, media_duration, FFmpegError

TICKS_PER_SECOND = 10_000_000


@dataclass
class SpokenWord:
    text: str
    start: float      # seconds from the start of this scene's audio
    duration: float


@dataclass
class SpeechChunk:
    """One scene's narration as rendered audio plus its word timings."""
    audio_path: Path
    duration: float          # including the trailing gap
    speech_duration: float   # without the gap
    words: list[SpokenWord] = field(default_factory=list)
    synthetic: bool = False  # True when TTS failed and this is silence


class TTSClient:
    def __init__(self) -> None:
        self.engine = settings.tts_engine

    # ─────────── scene-level API (used by the builder) ───────────

    async def synthesize_scene(
        self,
        text: str,
        output_path: Path,
        gap: Optional[float] = None,
    ) -> SpeechChunk:
        """Render one scene's narration to a wav, with word timings.

        Returns a silent chunk of a plausible length rather than raising if
        TTS is unreachable — a mute video still beats no video, and the rest
        of the timeline stays valid.
        """
        gap = settings.scene_gap if gap is None else gap
        clean = " ".join(text.replace("**", "").split())
        if not clean:
            clean = "…"

        raw_mp3 = output_path.with_suffix(".src.mp3")
        try:
            words = await self._edge_stream(clean, raw_mp3)
        except Exception as e:
            print(f"[TTS] synthesis failed ({e}); falling back to silence")
            return await self._silent_chunk(clean, output_path, gap)

        try:
            await self._to_wav(raw_mp3, output_path, gap)
            total = await media_duration(output_path)
        except FFmpegError as e:
            print(f"[TTS] wav conversion failed ({e}); falling back to silence")
            return await self._silent_chunk(clean, output_path, gap)
        finally:
            raw_mp3.unlink(missing_ok=True)

        return SpeechChunk(
            audio_path=output_path,
            duration=total,
            speech_duration=max(0.0, total - gap),
            words=words,
        )

    async def _edge_stream(self, text: str, mp3_path: Path) -> list[SpokenWord]:
        """Stream from edge-tts, keeping audio bytes and word boundaries."""
        import edge_tts

        communicate = edge_tts.Communicate(
            text,
            settings.tts_voice,
            rate=settings.tts_rate,
            pitch=settings.tts_pitch,
            boundary="WordBoundary",
        )

        audio = bytearray()
        words: list[SpokenWord] = []
        async for chunk in communicate.stream():
            kind = chunk.get("type")
            if kind == "audio":
                audio.extend(chunk["data"])
            elif kind == "WordBoundary":
                words.append(SpokenWord(
                    text=str(chunk.get("text", "")),
                    start=chunk["offset"] / TICKS_PER_SECOND,
                    duration=chunk["duration"] / TICKS_PER_SECOND,
                ))

        if not audio:
            raise RuntimeError("edge-tts returned no audio")
        mp3_path.write_bytes(bytes(audio))

        # Boundaries can be missing for a voice/locale combination; estimate
        # from the text so subtitles still appear, just less precisely.
        if not words:
            words = self._estimate_words(text, 0.0)
        return words

    async def _to_wav(self, src: Path, dst: Path, gap: float) -> None:
        """Decode to a canonical wav and append the inter-scene pause.

        Decoding out of mp3 first matters: mp3 carries encoder delay/padding,
        so measuring the compressed file would drift the whole timeline.
        """
        filters = ["aresample=48000", "aformat=sample_fmts=s16:channel_layouts=mono"]
        if gap > 0:
            filters.append(f"apad=pad_dur={gap:.3f}")
        await run_ffmpeg([
            "-i", str(src),
            "-af", ",".join(filters),
            "-c:a", "pcm_s16le",
            "-y", str(dst),
        ], timeout=180)

    async def _silent_chunk(
        self, text: str, output_path: Path, gap: float
    ) -> SpeechChunk:
        """Silence sized to how long the text would plausibly take to read."""
        words = self._estimate_words(text, 0.0)
        speech = sum(w.duration for w in words) or 2.0
        total = speech + gap
        await run_ffmpeg([
            "-f", "lavfi",
            "-i", f"anullsrc=r=48000:cl=mono",
            "-t", f"{total:.3f}",
            "-c:a", "pcm_s16le",
            "-y", str(output_path),
        ], timeout=120)
        return SpeechChunk(
            audio_path=output_path,
            duration=total,
            speech_duration=speech,
            words=words,
            synthetic=True,
        )

    @staticmethod
    def _estimate_words(text: str, offset: float) -> list[SpokenWord]:
        """Character-proportional timing — the fallback when TTS gives none."""
        tokens = text.split()
        if not tokens:
            return []
        # ~14 characters per second is close to edge-tts Russian at +8%.
        per_char = 1.0 / 14.0
        out: list[SpokenWord] = []
        cursor = offset
        for token in tokens:
            dur = max(0.18, len(token) * per_char + 0.06)
            out.append(SpokenWord(text=token, start=cursor, duration=dur))
            cursor += dur
        return out

    # ─────────── legacy single-shot API ───────────

    async def synthesize(
        self, text: str, output_path: Optional[Path] = None
    ) -> Path:
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".mp3"))

        if self.engine == "elevenlabs":
            await self._elevenlabs_tts(text, output_path)
        else:
            await self._edge_tts(text, output_path)
        return output_path

    async def _edge_tts(self, text: str, output_path: Path) -> None:
        try:
            import edge_tts

            communicate = edge_tts.Communicate(
                text, settings.tts_voice,
                rate=settings.tts_rate, pitch=settings.tts_pitch,
            )
            await communicate.save(str(output_path))
        except ImportError:
            cmd = [
                "edge-tts",
                "--voice", settings.tts_voice,
                "--text", text,
                "--write-media", str(output_path),
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            await proc.communicate()

    async def _elevenlabs_tts(self, text: str, output_path: Path) -> None:
        import httpx

        api_key = settings.elevenlabs_api_key
        voice_id = settings.elevenlabs_voice_id or "21m00Tcm4TlvDq8ikWAM"

        if not api_key:
            raise RuntimeError("ElevenLabs API key not configured")

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.3,
                        "similarity_boost": 0.7,
                    },
                },
            )
            resp.raise_for_status()
            output_path.write_bytes(resp.content)

    async def get_audio_duration(self, audio_path: Path) -> float:
        """Audio duration in seconds via ffprobe."""
        return await media_duration(audio_path)
