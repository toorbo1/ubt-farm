"""
Local AI Image Generation using diffusers.
Uses FLUX.1.1 Pro for maximum quality (locally installed models).
"""
import asyncio
import torch
from pathlib import Path
from typing import Optional
import numpy as np

from config.settings import settings


class LocalFLUXGenerator:
    """Local FLUX.1.1 Pro image generation via diffusers."""

    def __init__(self) -> None:
        self.model_id = "black-forest-labs/FLUX.1.1-pro"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipeline = None
        self._loaded = False

    def _load_pipeline(self) -> None:
        """Load the FLUX pipeline (lazy loading)."""
        if self._loaded:
            return

        from diffusers import FluxPipeline

        print(f"[LocalFLUX] Loading model on {self.device}...")
        self.pipeline = FluxPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
        ).to(self.device)

        if self.device == "cuda":
            self.pipeline.enable_model_cpu_offload()
            self.pipeline.enable_vae_tiling()

        self._loaded = True

    async def generate(
        self, prompt: str, output_path: Path, seed: Optional[int] = None
    ) -> Path:
        """Generate an image locally using FLUX.1.1 Pro."""
        import time

        self._load_pipeline()

        # Set seed for reproducibility
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)

        # Generate image with high quality settings
        print(f"[LocalFLUX] Generating image with seed={seed}")

        start_time = time.time()
        image = self.pipeline(
            prompt=prompt,
            width=settings.video_width,
            height=settings.video_height,
            num_inference_steps=50,  # Higher steps = better quality
            guidance_scale=7.5,
            generator=generator,
            max_sequence_length=512,
        ).images[0]

        elapsed = time.time() - start_time
        print(f"[LocalFLUX] Generated in {elapsed:.1f}s")

        # Save with high quality
        image.save(output_path, "JPEG", quality=98, subsampling=0, optimize=True)
        return output_path


class LocalSDXLGenerator:
    """Local Stable Diffusion XL generation via diffusers."""

    def __init__(self) -> None:
        self.model_id = "stabilityai/stable-diffusion-xl-base-1.0"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipeline = None
        self._loaded = False

    def _load_pipeline(self) -> None:
        """Load the SDXL pipeline (lazy loading)."""
        if self._loaded:
            return

        from diffusers import StableDiffusionXLPipeline

        print(f"[LocalSDXL] Loading model on {self.device}...")
        self.pipeline = StableDiffusionXLPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            use_safetensors=True,
        ).to(self.device)

        if self.device == "cuda":
            self.pipeline.enable_model_cpu_offload()
            self.pipeline.enable_vae_tiling()

        self._loaded = True

    async def generate(
        self, prompt: str, output_path: Path, seed: Optional[int] = None
    ) -> Path:
        """Generate an image locally using SDXL."""
        import time

        self._load_pipeline()

        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)

        print(f"[LocalSDXL] Generating image with seed={seed}")

        start_time = time.time()
        image = self.pipeline(
            prompt=prompt,
            width=settings.video_width,
            height=settings.video_height,
            num_inference_steps=40,
            guidance_scale=7.5,
            generator=generator,
        ).images[0]

        elapsed = time.time() - start_time
        print(f"[LocalSDXL] Generated in {elapsed:.1f}s")

        image.save(output_path, "JPEG", quality=98, subsampling=0, optimize=True)
        return output_path
