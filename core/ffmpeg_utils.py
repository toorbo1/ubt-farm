"""
ffmpeg/ffprobe helpers: async execution, probing, clip validation and
normalisation.

Every clip that enters the final assembly passes through `validate_clip`.
Without it a provider that answers HTTP 200 with a truncated, black or
wrongly-sized file counts as a success and corrupts the concat.
"""
from __future__ import annotations

import asyncio
import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config.settings import settings


class FFmpegError(RuntimeError):
    pass


@dataclass
class ClipInfo:
    duration: float
    width: int
    height: int
    fps: float
    nb_frames: int
    has_audio: bool

    @property
    def is_portrait(self) -> bool:
        return self.height > self.width


async def _run(cmd: list[str], timeout: int) -> tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise FFmpegError(f"timed out after {timeout}s: {shlex.join(cmd[:6])} ...")
    return proc.returncode, out, err


async def run_ffmpeg(args: list[str], timeout: int = 900) -> None:
    """Run ffmpeg with the given args (without the leading 'ffmpeg')."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin"] + args
    code, _, err = await _run(cmd, timeout)
    if code != 0:
        tail = err.decode(errors="replace").strip()[-800:]
        raise FFmpegError(f"ffmpeg exit {code}: {tail}")


async def probe(path: Path) -> ClipInfo:
    """Read stream/format metadata. Raises FFmpegError if unreadable."""
    cmd = [
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(path),
    ]
    code, out, err = await _run(cmd, 60)
    if code != 0:
        raise FFmpegError(f"ffprobe failed on {path.name}: "
                          f"{err.decode(errors='replace')[-300:]}")
    data = json.loads(out.decode(errors="replace") or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is None:
        raise FFmpegError(f"{path.name}: no video stream")

    duration = 0.0
    for candidate in (data.get("format", {}).get("duration"), video.get("duration")):
        try:
            duration = float(candidate)
            break
        except (TypeError, ValueError):
            continue

    fps = 0.0
    rate = video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1"
    try:
        num, _, den = rate.partition("/")
        fps = float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        fps = 0.0

    try:
        nb_frames = int(video.get("nb_frames") or 0)
    except (TypeError, ValueError):
        nb_frames = 0
    if not nb_frames and fps and duration:
        nb_frames = int(round(duration * fps))

    return ClipInfo(
        duration=duration,
        width=int(video.get("width") or 0),
        height=int(video.get("height") or 0),
        fps=fps,
        nb_frames=nb_frames,
        has_audio=audio is not None,
    )


async def media_duration(path: Path) -> float:
    """Container duration in seconds — works for audio-only files too."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1",
        str(path),
    ]
    code, out, err = await _run(cmd, 60)
    if code != 0:
        raise FFmpegError(f"ffprobe failed on {path.name}: "
                          f"{err.decode(errors='replace')[-300:]}")
    try:
        return float(out.decode(errors="replace").strip())
    except ValueError:
        raise FFmpegError(f"{path.name}: no readable duration")


async def mean_luma(path: Path, samples: int = 5) -> float:
    """Average luma over a handful of sampled frames (0-255).

    Used to reject clips that decode fine but are entirely black — a common
    failure shape for image-to-video APIs that time out server-side.
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-nostdin", "-i", str(path),
        "-vf", f"fps=1/max(1\\,{samples}),signalstats,metadata=print:key=lavfi.signalstats.YAVG",
        "-frames:v", str(samples), "-f", "null", "-",
    ]
    code, _, err = await _run(cmd, 120)
    if code != 0:
        return -1.0
    values = []
    for line in err.decode(errors="replace").splitlines():
        if "YAVG" in line and "=" in line:
            try:
                values.append(float(line.rsplit("=", 1)[1].strip()))
            except ValueError:
                pass
    if not values:
        return -1.0
    return sum(values) / len(values)


async def validate_clip(
    path: Path,
    min_duration: float = 0.8,
    min_luma: float = 6.0,
    require_portrait: bool = False,
) -> ClipInfo:
    """Raise FFmpegError unless the clip is genuinely usable footage."""
    if not path.exists():
        raise FFmpegError(f"{path.name}: file missing")
    size = path.stat().st_size
    if size < 20_000:
        raise FFmpegError(f"{path.name}: only {size} bytes")

    info = await probe(path)
    if info.duration < min_duration:
        raise FFmpegError(f"{path.name}: duration {info.duration:.2f}s "
                          f"< {min_duration}s")
    if info.width < 64 or info.height < 64:
        raise FFmpegError(f"{path.name}: bogus size {info.width}x{info.height}")
    if info.nb_frames < 2:
        raise FFmpegError(f"{path.name}: {info.nb_frames} frame(s) — a still, not video")
    if require_portrait and not info.is_portrait:
        raise FFmpegError(f"{path.name}: landscape {info.width}x{info.height}")

    luma = await mean_luma(path)
    if 0 <= luma < min_luma:
        raise FFmpegError(f"{path.name}: black frames (mean luma {luma:.1f})")
    return info


def _encoder_args(crf: int, preset: str) -> list[str]:
    """x264 args tuned for vertical social video.

    Software x264 on purpose: NVENC/AMF are faster but give noticeably worse
    quality per bit at these bitrates, and this pipeline is not latency-bound.
    """
    return [
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-profile:v", "high",
        "-level", "4.2",
        "-pix_fmt", "yuv420p",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-x264-params", "keyint=120:min-keyint=30:scenecut=40:ref=4:bframes=3",
    ]


async def conform_clip(
    src: Path,
    dst: Path,
    target_duration: float,
    crf: Optional[int] = None,
    preset: Optional[str] = None,
) -> Path:
    """Conform arbitrary provider output to the canonical clip format.

    Handles the three ways a provider clip can mismatch the timeline:
      * wrong size/fps        -> scale + crop to 1080x1920, resample fps
      * longer than needed    -> trimmed
      * shorter than needed   -> ping-pong looped (forward+reverse), which is
                                 seamless, unlike a frozen last frame

    Ping-pong rather than a plain loop because a plain loop snaps back to the
    first frame on every cycle; reversing keeps motion continuous.
    """
    W, H = settings.video_width, settings.video_height
    fps = settings.video_fps
    crf = settings.video_crf if crf is None else crf
    preset = settings.video_preset if preset is None else preset

    info = await probe(src)
    src_dur = max(0.05, info.duration)

    base = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={W}:{H},fps={fps},setsar=1"
    )

    if src_dur >= target_duration - 0.05:
        chain = f"[0:v]{base},trim=duration={target_duration:.3f},setpts=PTS-STARTPTS[v]"
    else:
        # How many forward+reverse pairs are needed to cover the target.
        cycles = 1
        while src_dur * (2 * cycles) < target_duration and cycles < 8:
            cycles += 1
        parts = [f"[0:v]{base},setpts=PTS-STARTPTS[base]"]
        parts.append(f"[base]split={2 * cycles}" +
                     "".join(f"[s{i}]" for i in range(2 * cycles)))
        labels = []
        for i in range(cycles):
            fwd, rev = f"s{2 * i}", f"s{2 * i + 1}"
            parts.append(f"[{rev}]reverse,setpts=PTS-STARTPTS[r{i}]")
            labels += [f"[{fwd}]", f"[r{i}]"]
        parts.append("".join(labels) +
                     f"concat=n={2 * cycles}:v=1:a=0,"
                     f"trim=duration={target_duration:.3f},setpts=PTS-STARTPTS[v]")
        chain = ";".join(parts)

    await run_ffmpeg([
        "-i", str(src),
        "-filter_complex", chain,
        "-map", "[v]",
        "-an",
        *_encoder_args(crf, preset),
        "-r", str(fps),
        "-y", str(dst),
    ], timeout=900)
    return dst


def escape_filter_path(path: Path) -> str:
    """Escape a filesystem path for use inside an ffmpeg filter argument.

    Windows paths need the drive colon escaped twice: once for the filter
    parser and once for the option parser.
    """
    text = str(path.resolve()).replace("\\", "/")
    text = text.replace(":", "\\:")
    return text.replace("'", "\\'")
