#!/usr/bin/env python3
"""
UBT Video Generator — Web App (Gradio)
Deploy on HuggingFace Spaces / Render / Railway for free.

Features:
- Gemini AI script generation with topic + traits input
- Pixel art image generation (enforced 2D, cartoon style)
- Local video assembly with ffmpeg
- TTS via edge-tts
- Download generated videos
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import gradio as gr
except ImportError:
    print("Installing gradio...")
    os.system("pip install gradio")
    import gradio as gr

from config.settings import settings
from core.gemini_client import GeminiClient
from video_engine.builder import VideoBuilder


# ─── Gemini API Key from env or user input ───
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY and settings.gemini_api_keys:
    keys = [k.strip() for k in settings.gemini_api_keys.split(",") if k.strip()]
    GEMINI_API_KEY = keys[0] if keys else ""


async def generate_script(topic: str, traits: str = "") -> tuple[str, str]:
    """Generate a viral script using Gemini AI."""
    if not topic or not topic.strip():
        return "⚠️ Введите тему для видео!", ""

    if not GEMINI_API_KEY:
        # Fallback to combinatorial templates
        from core.llm_client import LLMClient
        client = LLMClient()
        scenes = client._default_scenes(topic)
        text = " ".join(s["narration"] for s in scenes["scenes"])
        hook = text.split()[:3]
        return f" Hook: {' '.join(hook)}\n\n{text}", text

    try:
        gemini = GeminiClient()
        script = await gemini.generate_script(topic, traits or None)
        text = script.get("text", "")
        hook = script.get("hook", "")
        highlights = script.get("highlight_words", [])

        result = f"🎣 Hook: {hook}\n\n"
        result += f"`{text}`\n\n"
        if highlights:
            result += f"🔑 Ключевые слова: {', '.join(highlights)}"

        return result, text
    except Exception as e:
        return f" Ошибка генерации: {e}", ""


async def regenerate_script(old_text: str, topic: str, traits: str = "") -> tuple[str, str]:
    """Regenerate script with same topic but different approach."""
    if not GEMINI_API_KEY:
        return "⚠️ Нет Gemini API ключа. Добавьте GEMINI_API_KEY в .env", old_text

    try:
        gemini = GeminiClient()
        script = await gemini.regenerate_script(old_text, topic, traits or None)
        text = script.get("text", "")
        hook = script.get("hook", "")
        highlights = script.get("highlight_words", [])

        result = f"🎣 Hook: {hook}\n\n"
        result += f"`{text}`\n\n"
        if highlights:
            result += f"🔑 Ключевые слова: {', '.join(highlights)}"

        return result, text
    except Exception as e:
        return f"❌ Ошибка: {e}", old_text


async def create_video(topic: str, custom_script: str = "", progress=gr.Progress()) -> tuple[str | None, str]:
    """Create a full video from topic or custom script."""
    if not topic and not custom_script:
        return None, "️ Введите тему или сценарий!"

    output_dir = Path(settings.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        progress(0.1, desc="Инициализация...")
        builder = VideoBuilder()

        progress(0.2, desc="Генерация сценария...")
        if not custom_script and GEMINI_API_KEY:
            gemini = GeminiClient()
            script = await gemini.generate_script(topic)
            custom_script = script.get("text", "")

        progress(0.4, desc="Синтез речи (TTS)...")
        path = await builder.build(
            topic=topic,
            custom_script=custom_script,
            progress_callback=lambda msg: progress(None, desc=msg),
        )

        progress(0.9, desc="Готово!")
        return str(path), f"✅ Видео создано!\nРазмер: {path.stat().st_size / 1024 / 1024:.1f} MB"

    except Exception as e:
        return None, f"❌ Ошибка: {e}"


def build_ui() -> gr.Blocks:
    """Build the Gradio UI."""
    with gr.Blocks(title="UBT Video Generator", css=".gradio-container { max-width: 900px !important; }") as demo:
        gr.Markdown("# 🎬 UBT Video Generator")
        gr.Markdown("Создание вирусных видео с помощью ИИ — Gemini API + Pixel Art + FFmpeg")

        with gr.Tabs():
            # ─── Tab 1: Script Generator ───
            with gr.Tab("✨ Сценарий"):
                gr.Markdown("### Генератор сценариев через Gemini AI")

                with gr.Row():
                    topic_input = gr.Textbox(label="Тема видео", placeholder="Например: VPN безопасность, лайфхаки...", lines=2)
                    traits_input = gr.Textbox(label="Черты/стиль (необязательно)", placeholder="юмористический, с эмодзи, для детей...", lines=2)

                script_output = gr.Textbox(label="Сгенерированный сценарий", lines=8, interactive=False)
                script_state = gr.State(value="")

                with gr.Row():
                    gen_btn = gr.Button("✨ Сгенерировать", variant="primary")
                    regen_btn = gr.Button("🔄 Переделать")

                gen_btn.click(generate_script, inputs=[topic_input, traits_input], outputs=[script_output, script_state])
                regen_btn.click(regenerate_script, inputs=[script_state, topic_input, traits_input], outputs=[script_output, script_state])

            # ─── Tab 2: Video Creator ───
            with gr.Tab("🎬 Видео"):
                gr.Markdown("### Создание полного видео")

                with gr.Row():
                    video_topic = gr.Textbox(label="Тема видео", placeholder="О чём будет видео?", lines=2)
                    video_script = gr.Textbox(label="Свой сценарий (необязательно)", placeholder="Вставьте свой текст или оставьте пустым для авто-генерации", lines=6)

                video_output = gr.Video(label="Готовое видео", interactive=False)
                status_output = gr.Textbox(label="Статус", lines=3, interactive=False)

                create_btn = gr.Button("🎬 Создать видео", variant="primary")
                create_btn.click(create_video, inputs=[video_topic, video_script], outputs=[video_output, status_output])

            # ─── Tab 3: Settings ───
            with gr.Tab("⚙ Настройки"):
                gr.Markdown("### Конфигурация")

                gr.Textbox(label="Gemini API Key", value=GEMINI_API_KEY or "Не установлен", interactive=False, lines=2)
                gr.Markdown("""
                **Как получить Gemini API ключ:**
                1. Перейдите на https://makersuite.google.com/app/apikey
                2. Создайте новый API ключ
                3. Добавьте его в .env файл: `GEMINI_API_KEYS=ваш_ключ`
                """)

                gr.Markdown(f"""
                **Текущие настройки:**
                - TTS Engine: `{settings.tts_engine}`
                - Video Resolution: `{settings.video_width}x{settings.video_height}`
                - FPS: `{settings.video_fps}`
                - Output Dir: `{settings.output_dir}`
                """)

        gr.Markdown("---")
        gr.Markdown("Made with ❤️ | Deploy on [HuggingFace Spaces](https://huggingface.co/spaces) or [Render](https://render.com)")

    return demo


def main():
    demo = build_ui()
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))


if __name__ == "__main__":
    main()
