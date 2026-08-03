"""
AI #3: image-to-video.

Every provider produces a clip in its own size, frame rate and length, and
some of them fail by returning a 200 with unusable bytes. So nothing here is
trusted directly: each provider's output goes through `validate_clip` (real
duration, real frames, not black) and then `conform_clip` (canonical 1080x1920
at the exact length the timeline needs) before it can enter the assembly.

Providers deliberately NOT in the chain:
  * HuggingFace Inference video — the free image-to-video model ids that used
    to work are gone and the endpoint now requires a token; it only ever added
    ~90s of retry sleeps per scene before failing.
  * Local SVD on CPU — a single 4s shot takes hours. It is registered only
    when torch reports CUDA.
"""
from __future__ import annotations

import asyncio
import base64
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import httpx

from config.settings import settings
from core.ffmpeg_utils import (
    FFmpegError,
    conform_clip,
    validate_clip,
)
from core.motion import MotionPlan, plan_motion, render_motion_clip


class ImageToVideoGenerator(ABC):
    """A source of motion for one still frame.

    `index` and `avoid_move` are advisory: the local engine uses them to keep
    neighbouring shots from repeating a camera move, remote providers ignore
    them.
    """

    # How long this provider may run for one scene before it is abandoned.
    timeout: float = 300.0
    # True when the provider decides its own clip length regardless of ask.
    fixed_length: bool = False
    label: str = "generic"

    @abstractmethod
    async def generate(
        self,
        image_path: Path,
        prompt: str,
        output_path: Path,
        duration: float = 5.0,
        index: int = 0,
        avoid_move: Optional[str] = None,
    ) -> Path:
        ...


# ─────────────────────────── local motion engine ───────────────────────────


class LocalMotionGenerator(ImageToVideoGenerator):
    """Eased, graded camera moves rendered with ffmpeg.

    Always last in the chain and always available: no key, no network, no
    billing, and it produces the exact requested duration first time.
    """

    timeout = 900.0
    label = "local-motion"

    def __init__(self) -> None:
        self.last_plan: Optional[MotionPlan] = None

    async def generate(
        self,
        image_path: Path,
        prompt: str,
        output_path: Path,
        duration: float = 5.0,
        index: int = 0,
        avoid_move: Optional[str] = None,
    ) -> Path:
        plan = plan_motion(image_path, prompt, index=index, avoid=avoid_move)
        self.last_plan = plan
        print(f"[AI#3] local motion scene {index}: {plan.describe()}")
        return await render_motion_clip(image_path, output_path, duration, plan)


class LocalSVDImageToVideoGenerator(ImageToVideoGenerator):
    """Stable Video Diffusion, run locally. CUDA only — see module docstring.

    SVD-XT is trained for 25 frames at ~7fps (about 3.5s); asking for
    duration*fps frames, as this used to, produces either an OOM or garbage.
    The clip is generated at its native length and stretched by the caller.
    """

    timeout = 1800.0
    fixed_length = True
    label = "local-svd"

    def __init__(self) -> None:
        self.model_id = "stabilityai/stable-video-diffusion-img2vid-xt"
        self.pipeline = None
        self._loaded = False

    @staticmethod
    def available() -> bool:
        try:
            import torch
        except ImportError:
            return False
        return bool(torch.cuda.is_available())

    def _load_pipeline(self) -> None:
        if self._loaded:
            return
        import torch
        from diffusers import StableVideoDiffusionPipeline

        print("[LocalSVD] loading model on cuda...")
        self.pipeline = StableVideoDiffusionPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            variant="fp16",
        )
        self.pipeline.enable_model_cpu_offload()
        self.pipeline.enable_vae_slicing()
        self._loaded = True

    async def generate(
        self,
        image_path: Path,
        prompt: str,
        output_path: Path,
        duration: float = 5.0,
        index: int = 0,
        avoid_move: Optional[str] = None,
    ) -> Path:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._generate_sync, image_path, output_path
        )

    def _generate_sync(self, image_path: Path, output_path: Path) -> Path:
        import subprocess
        import torch
        from PIL import Image

        self._load_pipeline()

        # 576x1024 keeps the vertical framing; SVD tolerates it even though
        # it was trained on the 1024x576 landscape counterpart.
        image = Image.open(image_path).convert("RGB").resize((576, 1024),
                                                             Image.LANCZOS)
        native_fps = 7
        started = time.time()
        result = self.pipeline(
            image,
            num_frames=25,
            num_inference_steps=25,
            min_guidance_scale=1.0,
            max_guidance_scale=3.0,
            motion_bucket_id=127,
            noise_aug_strength=0.02,
            decode_chunk_size=4,
            fps=native_fps,
            generator=torch.manual_seed(abs(hash(image_path.name)) % (2 ** 31)),
        )
        print(f"[LocalSVD] {time.time() - started:.1f}s")

        frames_dir = output_path.parent / f"_svd_{output_path.stem}"
        frames_dir.mkdir(parents=True, exist_ok=True)
        try:
            for i, frame in enumerate(result.frames[0]):
                frame.save(frames_dir / f"f_{i:04d}.png")
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-framerate", str(native_fps),
                "-i", str(frames_dir / "f_%04d.png"),
                "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                "-pix_fmt", "yuv420p",
                str(output_path),
            ], check=True, capture_output=True, timeout=600)
        finally:
            for f in frames_dir.glob("*.png"):
                f.unlink()
            frames_dir.rmdir()
        return output_path


# ─────────────────────────── remote providers ───────────────────────────


class FalAIImageToVideoGenerator(ImageToVideoGenerator):
    """Image-to-video via the fal.ai async queue API (Kling and friends)."""

    timeout = 700.0
    fixed_length = True
    label = "fal"

    NEGATIVE = ("blurry, low quality, distorted, watermark, text overlay, "
                "morphing artifacts, extra limbs")

    def __init__(self) -> None:
        self.api_key = settings.fal_api_key
        self.model = settings.fal_video_model

    async def generate(
        self,
        image_path: Path,
        prompt: str,
        output_path: Path,
        duration: float = 5.0,
        index: int = 0,
        avoid_move: Optional[str] = None,
    ) -> Path:
        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }
        # Inline data URI — avoids a separate storage upload round trip.
        b64 = base64.b64encode(image_path.read_bytes()).decode()
        payload = {
            "image_url": f"data:image/jpeg;base64,{b64}",
            "prompt": _motion_prompt(prompt),
            "negative_prompt": self.NEGATIVE,
            # Kling only accepts 5 or 10 second jobs.
            "duration": "10" if duration > 7.5 else "5",
            "aspect_ratio": "9:16",
            "cfg_scale": 0.5,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            submit = await client.post(
                f"https://queue.fal.run/{self.model}", headers=headers, json=payload
            )
            submit.raise_for_status()
            job = submit.json()

            # Always follow the URLs fal returns — their shape varies per model.
            status_url = job.get("status_url")
            response_url = job.get("response_url")
            if not status_url:
                raise RuntimeError(f"fal.ai gave no status_url: {job}")

            deadline = settings.fal_poll_timeout
            waited = 0.0
            while waited < deadline:
                await asyncio.sleep(5)
                waited += 5
                st = await client.get(status_url, headers=headers)
                st.raise_for_status()
                state = st.json()
                status = state.get("status")
                if status == "COMPLETED":
                    result = state
                    if "video" not in result and response_url:
                        rr = await client.get(response_url, headers=headers)
                        rr.raise_for_status()
                        result = rr.json()
                    video = result.get("video") or {}
                    video_url = video.get("url") if isinstance(video, dict) else None
                    if not video_url:
                        raise RuntimeError(f"fal.ai returned no video URL: {result}")
                    dl = await client.get(video_url, timeout=300.0)
                    dl.raise_for_status()
                    output_path.write_bytes(dl.content)
                    return output_path
                if status in ("FAILED", "ERROR", "CANCELLED"):
                    raise RuntimeError(f"fal.ai job {status}: {state}")
            raise RuntimeError(f"fal.ai job timed out after {deadline}s")


class ReplicateImageToVideoGenerator(ImageToVideoGenerator):
    """Image-to-video via Replicate.

    The model is configurable because Replicate version hashes rotate; the
    default is SVD, which actually returns video. (The previous default was an
    SDXL *image* model, so a "successful" call wrote a PNG into an .mp4.)
    """

    timeout = 600.0
    fixed_length = True
    label = "replicate"

    def __init__(self) -> None:
        self.api_key = settings.replicate_api_key or ""
        self.model = settings.replicate_video_model

    async def generate(
        self,
        image_path: Path,
        prompt: str,
        output_path: Path,
        duration: float = 5.0,
        index: int = 0,
        avoid_move: Optional[str] = None,
    ) -> Path:
        if not self.api_key:
            raise RuntimeError("Replicate: no API key")

        b64_image = base64.b64encode(image_path.read_bytes()).decode()
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
            "Prefer": "wait=60",
        }
        payload = {
            "input": {
                "input_image": f"data:image/jpeg;base64,{b64_image}",
                "video_length": "25_frames_with_svd_xt",
                "sizing_strategy": "maintain_aspect_ratio",
                "frames_per_second": 7,
                "motion_bucket_id": 127,
            }
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"https://api.replicate.com/v1/models/{self.model}/predictions",
                headers=headers,
                json=payload,
            )
            if resp.status_code in (401, 403):
                raise RuntimeError("Replicate: invalid API key")
            resp.raise_for_status()
            prediction = resp.json()

            deadline, waited = 480, 0
            while waited < deadline:
                status = prediction.get("status")
                if status == "succeeded":
                    out = prediction.get("output")
                    url = out[0] if isinstance(out, list) and out else out
                    if not isinstance(url, str):
                        raise RuntimeError(f"Replicate: no output url ({out!r})")
                    dl = await client.get(url, timeout=300.0)
                    dl.raise_for_status()
                    output_path.write_bytes(dl.content)
                    return output_path
                if status in ("failed", "canceled"):
                    raise RuntimeError(
                        f"Replicate {status}: {prediction.get('error')}")

                await asyncio.sleep(5)
                waited += 5
                poll = await client.get(prediction["urls"]["get"], headers=headers)
                poll.raise_for_status()
                prediction = poll.json()
            raise RuntimeError("Replicate job timed out")


class RunwayImageToVideoGenerator(ImageToVideoGenerator):
    """Runway Gen-3 Alpha image-to-video."""

    timeout = 600.0
    fixed_length = True
    label = "runway"

    def __init__(self) -> None:
        self.api_key = settings.runway_api_key
        self.base_url = "https://api.runwayml.com/v1"

    async def generate(
        self,
        image_path: Path,
        prompt: str,
        output_path: Path,
        duration: float = 5.0,
        index: int = 0,
        avoid_move: Optional[str] = None,
    ) -> Path:
        async with httpx.AsyncClient(timeout=300.0) as client:
            files = {"image": (image_path.name, image_path.read_bytes(), "image/jpeg")}
            task_resp = await client.post(
                f"{self.base_url}/image_to_video",
                headers={"Authorization": f"Bearer {self.api_key}"},
                data={
                    "prompt": _motion_prompt(prompt),
                    "model": settings.runway_model,
                    "duration": int(round(duration)),
                },
                files=files,
            )
            task_resp.raise_for_status()
            task_id = task_resp.json()["id"]

            deadline, waited = 480, 0
            while waited < deadline:
                await asyncio.sleep(10)
                waited += 10
                status_resp = await client.get(
                    f"{self.base_url}/tasks/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                status_resp.raise_for_status()
                status_data = status_resp.json()
                if status_data["status"] == "succeeded":
                    video_url = status_data["output"]["video_url"]
                    video_resp = await client.get(video_url, timeout=300.0)
                    video_resp.raise_for_status()
                    output_path.write_bytes(video_resp.content)
                    return output_path
                if status_data["status"] == "failed":
                    raise RuntimeError(f"Runway failed: {status_data.get('error')}")
            raise RuntimeError("Runway job timed out")


class PikaImageToVideoGenerator(ImageToVideoGenerator):
    """Pika Labs image-to-video."""

    timeout = 600.0
    fixed_length = True
    label = "pika"

    def __init__(self) -> None:
        self.api_key = settings.pika_api_key
        self.base_url = "https://api.pika.art/v1"

    async def generate(
        self,
        image_path: Path,
        prompt: str,
        output_path: Path,
        duration: float = 5.0,
        index: int = 0,
        avoid_move: Optional[str] = None,
    ) -> Path:
        async with httpx.AsyncClient(timeout=300.0) as client:
            upload_resp = await client.post(
                f"{self.base_url}/files/upload",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": (image_path.name, image_path.read_bytes(), "image/jpeg")},
            )
            upload_resp.raise_for_status()
            file_key = upload_resp.json()["key"]

            task_resp = await client.post(
                f"{self.base_url}/videos/generate",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "image_key": file_key,
                    "prompt": _motion_prompt(prompt),
                    "duration": int(round(duration)),
                    "aspect_ratio": "9:16",
                },
            )
            task_resp.raise_for_status()
            task_id = task_resp.json()["id"]

            deadline, waited = 480, 0
            while waited < deadline:
                await asyncio.sleep(10)
                waited += 10
                status_resp = await client.get(
                    f"{self.base_url}/videos/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                status_resp.raise_for_status()
                status_data = status_resp.json()
                if status_data["status"] == "completed":
                    video_url = status_data["data"]["url"]
                    video_resp = await client.get(video_url, timeout=300.0)
                    video_resp.raise_for_status()
                    output_path.write_bytes(video_resp.content)
                    return output_path
                if status_data["status"] == "failed":
                    raise RuntimeError(f"Pika failed: {status_data.get('error')}")
            raise RuntimeError("Pika job timed out")


def _motion_prompt(scene_prompt: str) -> str:
    """Turn a still-image prompt into a motion brief.

    Image prompts describe a frame; video models need to be told what moves.
    Without this they tend to animate everything, which on pixel art reads as
    melting.
    """
    base = scene_prompt.strip()[:400]
    return (
        f"{base}. Subtle cinematic camera motion: slow dolly and gentle parallax. "
        "Keep the character stable and on-model, animate only ambient details "
        "(light flicker, small idle movement). No morphing, no warping."
    )


# ─────────────────────────── chain with validation ───────────────────────────


class ChainImageToVideoGenerator(ImageToVideoGenerator):
    """Runs providers in order; the first one whose output *validates* wins."""

    label = "chain"

    def __init__(self, generators: list[ImageToVideoGenerator]) -> None:
        self.generators = generators
        self.last_move: Optional[str] = None

    def describe(self) -> str:
        return " -> ".join(g.label for g in self.generators)

    async def generate(
        self,
        image_path: Path,
        prompt: str,
        output_path: Path,
        duration: float = 5.0,
        index: int = 0,
        avoid_move: Optional[str] = None,
    ) -> Path:
        errors: list[str] = []
        raw_path = output_path.with_name(f"{output_path.stem}_raw.mp4")

        for gen in self.generators:
            started = time.time()
            try:
                raw_path.unlink(missing_ok=True)
                await asyncio.wait_for(
                    gen.generate(
                        image_path, prompt, raw_path, duration,
                        index=index, avoid_move=avoid_move or self.last_move,
                    ),
                    timeout=gen.timeout,
                )
                await validate_clip(raw_path, min_duration=min(1.0, duration * 0.4))
                await conform_clip(raw_path, output_path, duration)
                await validate_clip(output_path, min_duration=duration * 0.9)

                if isinstance(gen, LocalMotionGenerator) and gen.last_plan:
                    self.last_move = gen.last_plan.move
                print(f"[AI#3] scene {index}: {gen.label} ok "
                      f"({time.time() - started:.1f}s)")
                return output_path
            except asyncio.TimeoutError:
                errors.append(f"{gen.label}: timeout after {gen.timeout}s")
            except Exception as e:
                errors.append(f"{gen.label}: {str(e)[:160]}")
            finally:
                raw_path.unlink(missing_ok=True)
            print(f"[AI#3] scene {index}: {errors[-1]}")

        raise RuntimeError("all video providers failed -> " + " | ".join(errors))


# ─────────────────────────── text-to-video (unused by builder) ───────────────


class VideoAIGenerator(ABC):
    @abstractmethod
    async def generate(self, prompt: str, output_path: Path,
                       duration: int = 10) -> Path:
        ...


def get_video_ai_generator() -> Optional[VideoAIGenerator]:
    return None


# ─────────────────────────── chain construction ───────────────────────────


def get_img2video_generator(
    prefer: Optional[str] = None,
) -> ChainImageToVideoGenerator:
    """Assemble the provider chain.

    `prefer` (from the bot's model menu) forces one provider to the front;
    the local engine still backstops it so a failure never kills the build.
    """
    chain: list[ImageToVideoGenerator] = []

    if settings.use_ai_video:
        if settings.use_local_video and LocalSVDImageToVideoGenerator.available():
            chain.append(LocalSVDImageToVideoGenerator())
        if settings.fal_api_key:
            chain.append(FalAIImageToVideoGenerator())
        if settings.replicate_api_key:
            chain.append(ReplicateImageToVideoGenerator())
        if settings.runway_api_key:
            chain.append(RunwayImageToVideoGenerator())
        if settings.pika_api_key:
            chain.append(PikaImageToVideoGenerator())

    chain.append(LocalMotionGenerator())

    if prefer:
        wanted = [g for g in chain if g.label == prefer]
        rest = [g for g in chain if g.label != prefer]
        if prefer == "local-motion":
            chain = wanted + rest
        elif wanted:
            chain = wanted + rest
    return ChainImageToVideoGenerator(chain)


def available_video_providers() -> list[tuple[str, bool, str]]:
    """(label, usable, reason) — drives the bot's model menu."""
    cuda_ok = LocalSVDImageToVideoGenerator.available()
    return [
        ("local-motion", True, "ffmpeg, всегда доступен"),
        ("fal", bool(settings.fal_api_key), "нужен FAL_API_KEY"),
        ("replicate", bool(settings.replicate_api_key), "нужен REPLICATE_API_KEY"),
        ("runway", bool(settings.runway_api_key), "нужен RUNWAY_API_KEY"),
        ("pika", bool(settings.pika_api_key), "нужен PIKA_API_KEY"),
        ("local-svd", cuda_ok, "нужна CUDA GPU" if not cuda_ok else "CUDA найдена"),
    ]
