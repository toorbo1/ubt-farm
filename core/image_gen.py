"""
AI #2: Image generation from text prompts.
Supports Stability AI, OpenAI DALL-E 3, and local fallback.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import httpx
import base64

from config.settings import settings


def _finalize_image(output_path: Path) -> Path:
    """Upscale to target resolution with AI-like enhancement + denoise."""
    from PIL import Image, ImageFilter

    W, H = settings.video_width, settings.video_height
    with Image.open(output_path) as im:
        im = im.convert("RGB")
        orig_size = im.size

        if im.size != (W, H):
            src_ratio = im.width / im.height
            dst_ratio = W / H
            if abs(src_ratio - dst_ratio) > 0.01:
                # Crop to 9:16 before scaling so nothing gets stretched
                if src_ratio > dst_ratio:
                    new_w = int(im.height * dst_ratio)
                    left = (im.width - new_w) // 2
                    im = im.crop((left, 0, left + new_w, im.height))
                else:
                    new_h = int(im.width / dst_ratio)
                    top = (im.height - new_h) // 2
                    im = im.crop((0, top, im.width, top + new_h))

            # Multi-step upscale for better quality (avoid blur from 2x scaling)
            if orig_size[0] < W // 2:  # If less than half size, use intermediate step
                # Step 1: Upscale to 1.5x
                mid_w, mid_h = int(orig_size[0] * 1.5), int(orig_size[1] * 1.5)
                im = im.resize((mid_w, mid_h), Image.LANCZOS)
                # Step 2: Final upscale to target
                im = im.resize((W, H), Image.LANCZOS)
            else:
                im = im.resize((W, H), Image.LANCZOS)

            # Enhanced sharpening tuned for low-res source (576x1024)
            im = im.filter(ImageFilter.UnsharpMask(radius=1.5, percent=85, threshold=2))
            # Subtle detail enhancement
            im = im.filter(ImageFilter.DETAIL)

        im.save(output_path, "JPEG", quality=95, subsampling=0, optimize=True)
    return output_path


def _enforce_pixel_art_style(prompt: str) -> str:
    """Enforce mandatory pixel art style keywords in image prompts.

    Always includes: 2D, pixel art, cartoon style, and the character description.
    This ensures consistent character appearance across all generated images.
    """
    # Mandatory keywords that MUST be present
    mandatory = [
        "2D",
        "pixel art",
        "cartoon style",
        "a cute small black pixel cat with glowing green eyes",
    ]

    # Check which keywords are missing
    prompt_lower = prompt.lower()
    missing = [kw for kw in mandatory if kw.lower() not in prompt_lower]

    # Add missing keywords to the beginning of the prompt
    if missing:
        prefix = ", ".join(missing) + ", "
        prompt = prefix + prompt

    # Ensure 9:16 aspect ratio is mentioned
    if "9:16" not in prompt and "vertical" not in prompt_lower:
        prompt += ", 9:16 vertical portrait"

    return prompt


class ImageGenerator(ABC):
    @abstractmethod
    async def generate(
        self, prompt: str, output_path: Path, seed: Optional[int] = None
    ) -> Path:
        ...


class StabilityGenerator(ImageGenerator):
    """Stability AI SD3.5 / SDXL image generation."""

    def __init__(self) -> None:
        self.api_key = settings.stability_api_key
        self.base_url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"

    async def generate(
        self, prompt: str, output_path: Path, seed: Optional[int] = None
    ) -> Path:
        prompt = _enforce_pixel_art_style(prompt)
        headers = {
            "authorization": f"Bearer {self.api_key}",
            "accept": "image/*",
        }
        data = {
            "prompt": prompt,
            "output_format": "jpeg",
            "aspect_ratio": "9:16",
            "model": settings.stability_model,
        }
        if seed is not None:
            data["seed"] = seed % 4294967295
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                self.base_url, headers=headers, data=data
            )
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
        return _finalize_image(output_path)


class DallE3Generator(ImageGenerator):
    """OpenAI DALL-E 3 image generation."""

    def __init__(self) -> None:
        self.api_key = settings.openai_api_key
        self.base_url = "https://api.openai.com/v1/images/generations"

    async def generate(
        self, prompt: str, output_path: Path, seed: Optional[int] = None
    ) -> Path:
        prompt = _enforce_pixel_art_style(prompt)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1792",  # 9:16 portrait
            "quality": "hd",
            "response_format": "b64_json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                self.base_url, headers=headers, json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            img_bytes = base64.b64decode(data["data"][0]["b64_json"])
            output_path.write_bytes(img_bytes)
        return _finalize_image(output_path)


class PollinationsImageGenerator(ImageGenerator):
    """Free image generation via pollinations.ai (no API key needed)."""

    _last_request_time = 0.0

    async def generate(
        self, prompt: str, output_path: Path, seed: Optional[int] = None
    ) -> Path:
        import urllib.parse, asyncio, time, secrets
        # Rate limit: wait at least 3s between requests
        elapsed = time.time() - self._last_request_time
        if elapsed < 3.0:
            await asyncio.sleep(3.0 - elapsed)
        self._last_request_time = time.time()

        # Enforce pixel art style first
        prompt = _enforce_pixel_art_style(prompt)

        # Enhance prompt for better quality
        enhanced = (
            f"masterpiece, best quality, ultra detailed, 8k, "
            f"professional digital art, sharp focus, dramatic lighting, "
            f"trending on artstation -- {prompt}"
        )
        # Truncate to avoid URL overflow
        enhanced = enhanced[:700]
        encoded = urllib.parse.quote(enhanced)

        async with httpx.AsyncClient(timeout=180.0) as client:
            for attempt in range(5):
                # Fresh seed per attempt: the server caches responses by full URL,
                # so a fixed URL returns a byte-identical image every time.
                attempt_seed = (seed if seed is not None else secrets.randbelow(2**31)) + attempt * 7919
                # Use proper aspect ratio parameters
                url = (
                    f"https://image.pollinations.ai/prompt/{encoded}"
                    f"?width={settings.video_width}&height={settings.video_height}"
                    f"&nologo=true&model=flux&seed={attempt_seed}"
                    f"&private=true&safe=false"
                )
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code == 429:
                    await asyncio.sleep(10 * (attempt + 1))
                    continue
                resp.raise_for_status()
                if len(resp.content) < 5000:
                    raise RuntimeError(f"Image too small ({len(resp.content)} bytes)")
                output_path.write_bytes(resp.content)
                # Force crop to 9:16 if aspect ratio is wrong
                return _finalize_image(output_path)
            raise RuntimeError(f"Pollinations rate limited: {resp.text[:200]}")


class OpenRouterImageGenerator(ImageGenerator):
    """Image generation via OpenRouter (Gemini Image, GPT-5 Image, etc.)."""

    def __init__(self) -> None:
        self.api_key = settings.openrouter_api_key or settings.llm_api_key
        self.model = settings.openrouter_image_model
        self.base_url = "https://openrouter.ai/api/v1"

    async def generate(
        self, prompt: str, output_path: Path, seed: Optional[int] = None
    ) -> Path:
        prompt = _enforce_pixel_art_style(prompt)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        aspect_prompt = f"{prompt}. Vertical 9:16 portrait orientation, high quality, detailed."
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": f"Generate an image: {aspect_prompt}. Return ONLY the image."}
            ],
            "max_tokens": 8192,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            msg = data["choices"][0]["message"]

            # Gemini format: message.images[]
            images = msg.get("images", [])
            if images:
                url = images[0].get("image_url", {}).get("url", "")
                if url.startswith("data:"):
                    import base64
                    b64 = url.split("base64,")[1]
                    img_bytes = base64.b64decode(b64)
                else:
                    async with httpx.AsyncClient(timeout=60.0) as dl:
                        r = await dl.get(url)
                        r.raise_for_status()
                        img_bytes = r.content
                output_path.write_bytes(img_bytes)
                return output_path

            # GPT format: content may contain markdown image
            content = msg.get("content", "")
            import re
            b64_match = re.search(r"data:image/(?:png|jpg|jpeg);base64,([A-Za-z0-9+/=]+)", content)
            if b64_match:
                import base64
                img_bytes = base64.b64decode(b64_match.group(1))
                output_path.write_bytes(img_bytes)
                return output_path

            raise RuntimeError(f"No image found in response: {data}")


class HuggingFaceImageGenerator(ImageGenerator):
    """Free image generation via HuggingFace Inference API (no API key needed for public models)."""

    MODELS = [
        "black-forest-labs/FLUX.1-schnell",  # Fastest free model
        "black-forest-labs/FLUX.1-dev",       # Higher quality
        "stabilityai/stable-diffusion-xl-base-1.0",
    ]

    def __init__(self) -> None:
        self.base_url = "https://api-inference.huggingface.co/models"
        self._current_model_idx = 0

    async def generate(
        self, prompt: str, output_path: Path, seed: Optional[int] = None
    ) -> Path:
        import asyncio
        prompt = _enforce_pixel_art_style(prompt)
        model = self.MODELS[self._current_model_idx % len(self.MODELS)]

        payload = {"inputs": prompt}
        if seed is not None:
            payload["parameters"] = {"seed": seed}

        async with httpx.AsyncClient(timeout=120.0) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(
                        f"{self.base_url}/{model}",
                        json=payload,
                        headers={"Accept": "image/*"},
                    )
                    if resp.status_code == 503:
                        # Model loading - wait and retry
                        wait_time = 20 + attempt * 10
                        await asyncio.sleep(wait_time)
                        continue
                    resp.raise_for_status()
                    output_path.write_bytes(resp.content)
                    return _finalize_image(output_path)
                except httpx.HTTPError:
                    if attempt < 2:
                        continue
                    raise
        raise RuntimeError("HuggingFace image generation failed after retries")

    def _rotate_model(self) -> None:
        """Rotate to next model on failure."""
        self._current_model_idx += 1


class GeminiImageGenerator(ImageGenerator):
    """Image generation via Google Gemini API with key rotation."""

    def __init__(self) -> None:
        raw = settings.gemini_api_keys
        self.keys = [k.strip() for k in raw.split(",") if k.strip()]
        self._key_index = 0

    def _make_prompt(self, prompt: str) -> str:
        # Enforce mandatory pixel art style keywords
        enforced = _enforce_pixel_art_style(prompt)
        return (
            f"{enforced}\n\n"
            "Style: detailed 2D pixel art, 16-bit retro game aesthetic, cartoon style, "
            "crisp pixel edges, rich colour palette, strong contrast, cinematic lighting. "
            "Vertical 9:16 portrait composition. No text, no watermark, no logo."
        )

    async def generate(
        self, prompt: str, output_path: Path, seed: Optional[int] = None
    ) -> Path:
        import asyncio
        model = settings.gemini_image_model
        if not self.keys:
            raise RuntimeError("No Gemini API keys configured")

        full_prompt = self._make_prompt(prompt)
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
        }
        if seed is not None:
            payload["generationConfig"]["seed"] = seed

        errors = []
        # Try every key exactly once, starting where the last call left off.
        for offset in range(len(self.keys)):
            key = self.keys[(self._key_index + offset) % len(self.keys)]
            try:
                async with httpx.AsyncClient(timeout=180.0) as client:
                    resp = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                        json=payload,
                        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    )
                if resp.status_code in (429, 503):
                    errors.append(f"key…{key[-6:]}: {resp.status_code} quota")
                    continue
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates") or []
                for part in (candidates[0].get("content", {}).get("parts", []) if candidates else []):
                    inline = part.get("inlineData")
                    if inline and inline.get("mimeType", "").startswith("image/"):
                        output_path.write_bytes(base64.b64decode(inline["data"]))
                        # Advance so the next scene starts on the following key
                        self._key_index = (self._key_index + offset + 1) % len(self.keys)
                        return _finalize_image(output_path)
                errors.append(f"key…{key[-6:]}: no image in response")
            except httpx.HTTPError as e:
                errors.append(f"key…{key[-6:]}: {e.__class__.__name__}")
            await asyncio.sleep(0)
        raise RuntimeError(f"Gemini failed on all {len(self.keys)} keys: {'; '.join(errors)}")


class LocalFallbackGenerator(ImageGenerator):
    """Draws a UNIQUE pixel-art scene per prompt using hash-based seeding."""

    # 8 distinct colour palettes
    PALETTES = [
        [(10,10,40),(20,20,80),(30,40,120),(0,80,160),(0,120,200),(80,180,255),(200,220,255)],
        [(40,10,10),(70,20,15),(120,50,20),(180,90,30),(220,150,50),(255,210,120),(255,230,180)],
        [(10,40,10),(20,70,20),(30,100,40),(50,140,60),(100,200,80),(180,230,140),(220,255,200)],
        [(40,30,40),(60,40,60),(90,60,90),(120,80,120),(160,120,160),(210,180,210),(240,220,240)],
        [(20,20,20),(30,40,50),(0,60,80),(0,100,130),(0,150,200),(100,220,255),(200,240,255)],
        [(50,40,20),(90,70,30),(140,110,50),(190,150,70),(220,190,110),(240,220,160),(255,240,200)],
        [(20,20,50),(40,40,80),(70,60,110),(100,90,150),(140,130,200),(190,180,230),(230,220,255)],
        [(50,50,20),(80,80,30),(110,100,40),(150,130,60),(200,170,80),(230,210,130),(255,240,180)],
    ]

    # Cat pixel sprite (7 wide x 10 tall) - black cat facing forward
    # 1=body, 2=ear_inner, 3=eye_green, 4=nose, 5=mouth, 6=whisker, 0=transparent
    CAT_SPRITE_SIT = [
        [0,0,1,1,1,0,0],
        [0,2,1,1,1,2,0],
        [1,1,1,1,1,1,1],
        [1,3,1,4,1,3,1],
        [1,1,5,5,5,1,1],
        [0,6,1,1,1,6,0],
        [0,1,1,1,1,1,0],
        [0,0,1,1,1,0,0],
        [0,0,1,0,1,0,0],
        [0,0,1,0,1,0,0],
    ]
    CAT_SPRITE_JUMP = [
        [0,0,0,1,0,0,0],
        [0,1,1,1,1,1,0],
        [1,3,1,4,1,3,1],
        [1,1,5,5,5,1,1],
        [0,6,1,1,1,6,0],
        [0,0,1,1,1,0,0],
        [1,0,1,0,1,0,1],
        [0,0,1,0,1,0,0],
        [0,0,0,1,0,0,0],
        [0,0,0,1,0,0,0],
    ]
    CAT_COLORS = {
        1: (16,16,16),
        2: (200,150,150),
        3: (50,255,50),
        4: (255,120,120),
        5: (30,30,30),
        6: (200,200,200),
    }

    async def generate(
        self, prompt: str, output_path: Path, seed: Optional[int] = None
    ) -> Path:
        import hashlib, random
        from PIL import Image, ImageDraw

        # Deterministic seed from prompt hash -> guaranteed different image per prompt
        base = f"{prompt}|{seed}" if seed is not None else prompt
        seed_val = int(hashlib.md5(base.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed_val)

        W, H = 1080, 1920
        PX = 10
        COLS, ROWS = W // PX, H // PX

        img = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)

        def rect(x, y, w_px=1, h_px=1, fill=(0,0,0)):
            draw.rectangle([x*PX, y*PX, (x+w_px)*PX-1, (y+h_px)*PX-1], fill=fill)

        # ── 1. Background gradient ──
        pal_idx = rng.randint(0, len(self.PALETTES) - 1)
        pal = self.PALETTES[pal_idx]
        rng.shuffle(pal)
        for gy in range(ROWS):
            t = gy / ROWS
            ci = min(int(t * len(pal)), len(pal)-1)
            r0,g0,b0 = pal[ci]
            fade = 1.0 - 0.25 * (gy / ROWS)
            rect(0, gy, COLS, 1, (int(r0*fade), int(g0*fade), int(b0*fade)))

        # ── 2. Ground ──
        ground_top = int(ROWS * (0.65 + rng.random() * 0.15))
        gc = pal[rng.randint(0, len(pal)-1)]
        rect(0, ground_top, COLS, ROWS - ground_top, gc)

        # slight ground variation
        for _ in range(10):
            gx = rng.randint(0, COLS-2)
            gy = ground_top + rng.randint(0, min(ROWS-ground_top-1, 6))
            rect(gx, gy, rng.randint(1,3), 1, tuple(min(255, c+15) for c in gc))

        # ── 3. Background objects (3-6) ──
        num_objects = rng.randint(3, 6)
        object_types = ["star","window","tree","box","circle","diamond","line"]
        for _ in range(num_objects):
            ot = rng.choice(object_types)
            ox = rng.randint(1, COLS-3)
            oy = rng.randint(1, ground_top-5)
            oc = pal[rng.randint(0, len(pal)-1)]
            oc_bright = tuple(min(255, c+60) for c in oc)
            if ot == "star":
                rect(ox, oy, 1, 1, (255,255,200))
                rect(ox, oy-1, 1, 1, (255,255,200))
                rect(ox-1, oy, 1, 1, (255,255,200))
                rect(ox+1, oy, 1, 1, (255,255,200))
            elif ot == "window":
                rect(ox, oy, 3, 4, oc)
                rect(ox+1, oy+1, 1, 2, oc_bright)
                if rng.random() < 0.5:
                    rect(ox, oy+2, 3, 1, (80,80,80))
            elif ot == "tree":
                th = rng.randint(3, 7)
                rect(ox+1, oy+th-2, 1, 2, (60,40,20))
                rect(ox, oy, 3, th-2, (40,80,20))
                if rng.random() < 0.5:
                    rect(ox, oy-1, 3, 1, (60,120,30))
            elif ot == "box":
                bw, bh = rng.randint(3,6), rng.randint(2,4)
                rect(ox, oy, bw, bh, oc)
                if bw > 2 and bh > 2:
                    rect(ox+1, oy+1, bw-2, bh-2, oc_bright)
            elif ot == "circle":
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        if dx*dx + dy*dy <= 4:
                            rect(ox+dx, oy+dy, 1, 1, oc_bright if dx==0 and dy==0 else oc)
            elif ot == "diamond":
                for r2 in range(3):
                    for dx in range(-r2, r2+1):
                        rect(ox+dx, oy+r2-2, 1, 1, oc_bright if r2==0 else oc)
                        rect(ox+dx, oy-r2+2, 1, 1, oc_bright if r2==0 else oc)
            else:  # line
                ly = oy + rng.randint(0, 3)
                rect(ox, ly, rng.randint(2,6), 1, oc)

        # ── 4. Foreground objects (2-4 near bottom) ──
        num_fg = rng.randint(2, 4)
        for _ in range(num_fg):
            fx = rng.randint(1, COLS-4)
            fy = ground_top + rng.randint(1, ROWS-ground_top-3)
            fw, fh = rng.randint(1, 3), rng.randint(1, 2)
            fc = pal[rng.randint(0, len(pal)-1)]
            rect(fx, fy, fw, fh, fc)
            if rng.random() < 0.4:
                rect(fx, fy-1, fw, 1, tuple(min(255, c+40) for c in fc))

        # ── 5. Draw the black cat at a RANDOM position ──
        cat_sprite = rng.choice([self.CAT_SPRITE_SIT, self.CAT_SPRITE_JUMP])
        cat_w, cat_h = len(cat_sprite[0]), len(cat_sprite)
        cat_cx = rng.randint(cat_w, COLS - cat_w - 1)
        cat_cy = max(1, ground_top - cat_h - rng.randint(0, 4))

        for dy in range(cat_h):
            for dx in range(cat_w):
                val = cat_sprite[dy][dx]
                if val != 0:
                    rect(cat_cx + dx, cat_cy + dy, 1, 1, self.CAT_COLORS[val])

        # ── 6. Particles ──
        for _ in range(rng.randint(15, 35)):
            sx = rng.randint(1, COLS-2)
            sy = rng.randint(1, ROWS-3)
            sc = rng.choice([(255,255,100),(100,200,255),(255,150,255),(255,255,255)])
            rect(sx, sy, 1, 1, sc)

        # ── 7. Border frame ──
        fc2 = pal[rng.randint(0, len(pal)-1)]
        rect(0, 0, 1, ROWS, fc2)
        rect(0, 0, COLS, 1, fc2)
        rect(COLS-1, 0, 1, ROWS, fc2)
        rect(0, ROWS-1, COLS, 1, fc2)

        img.save(output_path, "JPEG", quality=90)
        return output_path


class ReplicateImageGenerator(ImageGenerator):
    """High-quality image generation via Replicate (SDXL/FLUX)."""

    def __init__(self) -> None:
        self.api_key = settings.replicate_api_key
        self.base_url = "https://api.replicate.com/v1/predictions"
        # SDXL для высокого качества 1080x1920
        self.model = "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"

    async def generate(
        self, prompt: str, output_path: Path, seed: Optional[int] = None
    ) -> Path:
        if not self.api_key or "YourTokenHere" in self.api_key:
            raise RuntimeError("Replicate API key не настроен")

        prompt = _enforce_pixel_art_style(prompt)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Prefer": "wait",  # Ждать завершения вместо polling
        }

        payload = {
            "version": self.model.split(":")[1],
            "input": {
                "prompt": prompt,
                "width": 1080,
                "height": 1920,
                "refine": "expert_ensemble_refiner",
                "scheduler": "K_EULER",
                "num_inference_steps": 50,
                "guidance_scale": 7.5,
            },
        }
        if seed is not None:
            payload["input"]["seed"] = seed

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Создать prediction
            resp = await client.post(self.base_url, headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()

            # Получить URL картинки
            output_url = result.get("output")
            if isinstance(output_url, list):
                output_url = output_url[0]
            elif not output_url:
                raise RuntimeError("No output URL from Replicate")

            # Скачать картинку
            img_resp = await client.get(output_url)
            img_resp.raise_for_status()
            output_path.write_bytes(img_resp.content)

        return _finalize_image(output_path)


class ChainImageGenerator(ImageGenerator):
    """Tries each provider in order, falling back on failure."""

    def __init__(self, generators: list[ImageGenerator]) -> None:
        self.generators = generators

    async def generate(
        self, prompt: str, output_path: Path, seed: Optional[int] = None
    ) -> Path:
        errors = []
        for gen in self.generators:
            try:
                return await gen.generate(prompt, output_path, seed)
            except Exception as e:
                errors.append(f"{gen.__class__.__name__}: {str(e)[:120]}")
        raise RuntimeError("All image providers failed -> " + " | ".join(errors))


def get_image_generator() -> ImageGenerator:
    """Get image generator chain with local fallback for offline mode."""
    generators: list[ImageGenerator] = []

    # 1. Gemini (если есть ключи)
    raw_keys = settings.gemini_api_keys
    if raw_keys and any(k.strip() for k in raw_keys.split(",")):
        generators.append(GeminiImageGenerator())

    # 2. Pollinations (бесплатно, без ключа, но требует интернет)
    generators.append(PollinationsImageGenerator())

    # 3. Local fallback — всегда доступен, работает офлайн
    generators.append(LocalFallbackGenerator())

    return ChainImageGenerator(generators)
