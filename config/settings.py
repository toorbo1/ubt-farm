from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # LLM (AI #1) — Google Gemini или OpenRouter/другие
    llm_api_key: str = "AQ.Ab8RN6IxzM4_1uRShXgeB9kDR3Zy-YZdge36FwDvEJxhXFUpHg"
    llm_model: str = "gemini-2.5-flash"
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/models"

    # OpenRouter image gen (AI #2)
    openrouter_api_key: str = ""
    openrouter_image_model: str = "black-forest-labs/flux-schnell"

    # TTS
    tts_engine: str = "edge"
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None

    # AI Image Gen (AI #2) — Gemini native image generation
    gemini_api_keys: str = ""  # comma-separated Google AI keys for rotation
    gemini_image_model: str = "gemini-3.1-flash-image-preview"

    # AI Image Gen (AI #2) — fallback providers
    pollinations_model: str = "flux"
    stability_api_key: Optional[str] = None
    stability_model: str = "sd3.5-large"
    openai_api_key: Optional[str] = None

    # AI Image Gen — HuggingFace Inference needs a token since 2024;
    # without one the endpoint 401s, so the provider stays out of the chain.
    hf_api_key: Optional[str] = None

    # AI Video Gen (AI #3)
    use_ai_video: bool = True  # False = local motion engine only, skip paid APIs
    replicate_api_key: Optional[str] = None  # Replicate API for video gen
    replicate_video_model: str = "stability-ai/stable-video-diffusion"
    # Local SVD is only viable on CUDA — on CPU a single 4s shot takes hours.
    # get_img2video_generator() also hard-checks torch.cuda before using it.
    use_local_video: bool = False
    fal_api_key: str = ""
    fal_video_model: str = "fal-ai/kling-video/v1/standard/image-to-video"
    fal_poll_timeout: int = 600
    runway_api_key: Optional[str] = None
    runway_model: str = "gen3"
    pika_api_key: Optional[str] = None

    # Local generation settings
    local_image_model: str = "flux"  # flux or sdxl

    # ─── Motion engine (local image-to-video) ───
    quality_preset: str = "balanced"  # fast | balanced | cinema
    motion_intensity: float = 0.75    # 0-1, scales how far the camera travels
    motion_grain: float = 0.35        # 0-1, temporal film grain
    motion_vignette: float = 0.40     # 0-1, corner falloff
    motion_grade: bool = True         # contrast/saturation lift

    # ─── Assembly ───
    video_crf: int = 18
    video_preset: str = "medium"
    transitions_enabled: bool = True
    transition_duration: float = 0.45  # xfade overlap between scenes
    scene_gap: float = 0.22            # silence appended after each narration
    loudness_lufs: float = -14.0       # social platform loudness target
    subtitle_words_per_chunk: int = 3

    # ─── TTS ───
    tts_voice: str = "ru-RU-DmitryNeural"
    tts_rate: str = "+8%"
    tts_pitch: str = "+0Hz"

    # Uploader
    upload_headless: bool = False
    upload_proxy: Optional[str] = None
    upload_profile_dir: str = "./profiles"

    # Storage
    backgrounds_dir: str = "./assets/backgrounds"
    output_dir: str = "./output"
    fonts_dir: str = "./assets/fonts"

    # Telegram
    telegram_bot_token: str = ""
    telegram_bot_token_2: str = ""
    telegram_bot_username: str = "vpn_bot"
    telegram_link: str = "t.me/vpn_bot"
    telegram_chat_id: Optional[int] = None  # auto-post generated videos here

    # VPN Monitor API
    vpn_api_url: str = "https://127.0.0.1:8443"
    vpn_api_key: str = "ventura-api-key-2025"

    # Video params
    video_width: int = 1080
    video_height: int = 1920
    video_fps: int = 30
    subtitle_font_size: int = 68
    subtitle_font: str = "Arial"
    subtitle_margin_v: int = 500
    subtitle_highlight_color: str = "#FFD700"
    subtitle_main_color: str = "#FFFFFF"
    cta_duration: int = 4

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
