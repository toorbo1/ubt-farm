"""
Cinematic motion engine: turns a still frame into a moving shot.

This is the workhorse of the pipeline — on a machine without a GPU it is the
*only* path that produces motion at a usable speed, so it has to look
deliberate rather than like a screensaver zoom. Three things do most of that
work here:

  * eased motion — a linear `on/frames` ramp reads as robotic; every move
    below runs through smoothstep so it accelerates and settles
  * supersampling — zoompan crops on integer pixel boundaries, so panning a
    1080-wide source jitters; cropping from a 2x source halves the step
  * a light grade — grain, vignette and a touch of contrast hide the flatness
    of a diffusion still and make consecutive shots feel like one piece
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config.settings import settings
from core.ffmpeg_utils import run_ffmpeg, _encoder_args


# Each move is (name, weight). Pushes are weighted up: they read as
# intentional camera work, while pure pans can look like a slideshow.
MOVES: tuple[tuple[str, int], ...] = (
    ("push_in", 5),
    ("pull_out", 3),
    ("pan_left", 2),
    ("pan_right", 2),
    ("pan_up", 2),
    ("pan_down", 2),
    ("push_in_left", 3),
    ("push_in_right", 3),
    ("pull_out_up", 2),
)


@dataclass
class MotionPlan:
    move: str
    zoom_max: float
    seed: int

    def describe(self) -> str:
        return f"{self.move} @ {self.zoom_max:.2f}x"


def plan_motion(
    image_path: Path,
    prompt: str,
    index: int = 0,
    avoid: Optional[str] = None,
    intensity: Optional[float] = None,
) -> MotionPlan:
    """Pick a camera move deterministically from the scene identity.

    Deterministic so a retry of the same scene produces the same shot, and
    `avoid` so two neighbouring scenes never repeat a move — back-to-back
    identical pushes are the single most obvious tell of generated video.
    """
    intensity = settings.motion_intensity if intensity is None else intensity
    intensity = max(0.05, min(1.0, intensity))

    key = f"{image_path.name}|{prompt}|{index}".encode()
    seed = int(hashlib.md5(key).hexdigest()[:8], 16)
    rng = random.Random(seed)

    names = [m for m, _ in MOVES]
    weights = [w for _, w in MOVES]
    if avoid in names:
        i = names.index(avoid)
        names.pop(i)
        weights.pop(i)
    move = rng.choices(names, weights=weights, k=1)[0]

    # 8%-26% travel at full intensity: enough to feel alive, little enough
    # that a 1080p source never gets upscaled past its detail.
    zoom_max = 1.0 + (0.08 + rng.random() * 0.18) * intensity
    return MotionPlan(move=move, zoom_max=round(zoom_max, 4), seed=seed)


def _smoothstep(frames: int) -> str:
    """Smoothstep on normalised output-frame position: p*p*(3-2p)."""
    p = f"(on/{frames})"
    return f"({p}*{p}*(3-2*{p}))"


def build_zoompan(plan: MotionPlan, frames: int, out_w: int, out_h: int, fps: int) -> str:
    """Build the zoompan filter string for a planned move.

    zoompan crops an (iw/zoom x ih/zoom) window at (x, y) from the *input*
    and rescales it to `s` — so x/y expressions are in input coordinates and
    the maximum offset is (iw - iw/zoom).
    """
    ease = _smoothstep(frames)
    zmax = plan.zoom_max

    centre_x = "iw/2-(iw/zoom/2)"
    centre_y = "ih/2-(ih/zoom/2)"
    zoom_in = f"(1+{zmax - 1.0:.4f}*{ease})"
    zoom_out = f"({zmax:.4f}-{zmax - 1.0:.4f}*{ease})"

    # Pans need a standing zoom, otherwise there is nothing to pan across.
    pan_zoom = f"{1.0 + (zmax - 1.0) * 0.9:.4f}"
    span_x = "(iw-iw/zoom)"
    span_y = "(ih-ih/zoom)"

    if plan.move == "push_in":
        z, x, y = zoom_in, centre_x, centre_y
    elif plan.move == "pull_out":
        z, x, y = zoom_out, centre_x, centre_y
    elif plan.move == "pan_left":
        z, x, y = pan_zoom, f"{span_x}*(1-{ease})", centre_y
    elif plan.move == "pan_right":
        z, x, y = pan_zoom, f"{span_x}*{ease}", centre_y
    elif plan.move == "pan_up":
        z, x, y = pan_zoom, centre_x, f"{span_y}*(1-{ease})"
    elif plan.move == "pan_down":
        z, x, y = pan_zoom, centre_x, f"{span_y}*{ease}"
    elif plan.move == "push_in_left":
        z, x, y = zoom_in, f"{span_x}*(1-{ease})", centre_y
    elif plan.move == "push_in_right":
        z, x, y = zoom_in, f"{span_x}*{ease}", centre_y
    else:  # pull_out_up
        z, x, y = zoom_out, centre_x, f"{span_y}*(1-{ease})"

    return (
        f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={out_w}x{out_h}:fps={fps}"
    )


def build_grade(seed: int) -> str:
    """Grain + vignette + a gentle contrast lift, in that order.

    Grain goes last so it is not smeared by the rescale, and it is temporal
    (`allf=t`) — static grain looks like sensor dirt, not film.
    """
    parts = []
    if settings.motion_grade:
        parts.append("eq=contrast=1.06:saturation=1.08:gamma=0.985")
    if settings.motion_vignette > 0:
        parts.append(f"vignette=angle=PI/{max(2.0, 6.0 - settings.motion_vignette * 2):.2f}")
    parts.append("unsharp=5:5:0.45:3:3:0.15")
    if settings.motion_grain > 0:
        strength = max(1, int(settings.motion_grain * 12))
        parts.append(f"noise=alls={strength}:allf=t+u")
    return ",".join(parts)


async def render_motion_clip(
    image_path: Path,
    output_path: Path,
    duration: float,
    plan: MotionPlan,
    quality: Optional[str] = None,
) -> Path:
    """Render a single moving shot from a still image."""
    W, H = settings.video_width, settings.video_height
    fps = settings.video_fps
    frames = max(2, int(round(duration * fps)))

    quality = quality or settings.quality_preset
    if quality == "fast":
        ss, crf, preset = 1, 20, "veryfast"
    elif quality == "cinema":
        ss, crf, preset = 2, 15, "slow"
    else:  # balanced
        ss, crf, preset = 2, 17, "medium"

    # Supersample, then let zoompan crop out of the larger frame.
    pre = (
        f"scale={W * ss}:{H * ss}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={W * ss}:{H * ss},setsar=1"
    )
    vf = ",".join([
        pre,
        build_zoompan(plan, frames, W, H, fps),
        build_grade(plan.seed),
        "format=yuv420p",
    ])

    await run_ffmpeg([
        "-loop", "1",
        "-framerate", str(fps),
        "-t", f"{duration:.3f}",
        "-i", str(image_path),
        "-vf", vf,
        "-frames:v", str(frames),
        "-an",
        *_encoder_args(crf, preset),
        "-r", str(fps),
        "-y", str(output_path),
    ], timeout=900)
    return output_path
