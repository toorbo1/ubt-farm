"""
Deprecated shim.

The local video paths live in two places now:
  * core.motion              — the ffmpeg camera-move engine (CPU, fast)
  * core.video_ai            — the provider chain, including CUDA-gated SVD

This module used to hold a second, drifting copy of both. It re-exports the
real implementations so any old import keeps working, and so the CPU-only SVD
path (hours per shot) cannot be reintroduced by accident.
"""
from core.video_ai import (  # noqa: F401
    LocalMotionGenerator as LocalVideoFromImagesGenerator,
    LocalSVDImageToVideoGenerator as LocalSVDGenerator,
)

__all__ = ["LocalVideoFromImagesGenerator", "LocalSVDGenerator"]
