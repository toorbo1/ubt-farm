import asyncio, sys, json, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import settings
from core.llm_client import LLMClient
from core.image_gen import get_image_generator, LocalFallbackGenerator
from core.video_ai import get_img2video_generator

OUTPUT = Path("output") / "test"
OUTPUT.mkdir(parents=True, exist_ok=True)

async def test_ai1():
    print("\n=== AI#1: LLM (OpenRouter) ===")
    print(f"Model: {settings.llm_model}")
    client = LLMClient()
    try:
        scenes = await client.generate_scenes("VPN i privatnost")
        data = scenes.get("scenes", [])
        print(f"Scenes: {len(data)}")
        for i, s in enumerate(data, 1):
            print(f"  [{i}] ({s.get('duration',3)}s) {s.get('narration','')[:60]}...")
            print(f"       img: {s.get('image_prompt','')[:80]}...")
        print(f"Highlight: {scenes.get('highlight_words', [])}")
        print("AI#1 OK")
        return scenes
    except Exception as e:
        print(f"AI#1 FAILED: {e}")
        import traceback; traceback.print_exc()
        return None
    finally:
        await client.close()

async def test_ai2():
    print("\n=== AI#2: Image Generation ===")
    gen = get_image_generator()
    print(f"Generator: {type(gen).__name__}")
    prompt = "Cinematic shot of a young woman using a laptop in a cozy room, warm lighting, photorealistic, 8K, 9:16"
    out = OUTPUT / "test_img.jpg"
    try:
        result = await gen.generate(prompt, out)
        sz = result.stat().st_size
        print(f"Saved: {result.name} ({sz} bytes)")
        print(f"OK" if sz > 5000 else f"WARNING: too small ({sz})")
        return result
    except Exception as e:
        print(f"AI#2 FAILED: {e}")
        import traceback; traceback.print_exc()
        return None

async def test_ai3(img_path: Path):
    print("\n=== AI#3: Video Generation (fal.ai) ===")
    gen = get_img2video_generator()
    print(f"Generator: {type(gen).__name__}")
    if not img_path or not img_path.exists():
        print("SKIP: no image")
        return
    out = OUTPUT / "test_vid.mp4"
    try:
        print("Sending to fal.ai (30-60s)...")
        result = await gen.generate(img_path, "cinematic slow zoom on person at computer, subtle camera move", out, 5)
        sz = result.stat().st_size
        print(f"Video: {result.name} ({sz} bytes)")
        print("OK" if sz > 10000 else f"WARNING: too small ({sz})")
    except Exception as e:
        print(f"AI#3 FAILED: {e}")
        import traceback; traceback.print_exc()

async def test_fallback():
    print("\n=== Fallback image ===")
    gen = LocalFallbackGenerator()
    out = OUTPUT / "fallback.jpg"
    r = await gen.generate("test", out)
    print(f"Saved: {r.name} ({r.stat().st_size} bytes)")

async def main():
    print(f"LLM key: {'SET' if settings.llm_api_key else 'EMPTY'}")
    print(f"fal key: {'SET' if settings.fal_api_key else 'EMPTY'}")
    print(f"Img model: {settings.openrouter_image_model}")
    
    s = await test_ai1()
    img = await test_ai2()
    await test_ai3(img)
    await test_fallback()

if __name__ == "__main__":
    asyncio.run(main())
