"""Test Gemini image generation."""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.image_gen import GeminiImageGenerator

gen = GeminiImageGenerator()

async def test():
    prompt = (
        "2D pixel art, 16-bit retro game style, "
        "a cute small black pixel cat with glowing green eyes sitting on a giant glowing keyboard, "
        "pixel sparks flying from keys, dark room with neon cyan glow from monitors, "
        "pixel shelves with retro game cartridges, 9:16 vertical pixel art"
    )
    out = "test_output/gemini_test.jpg"
    os.makedirs("test_output", exist_ok=True)
    try:
        result = await gen.generate(prompt, out)
        print(f"SUCCESS: {result}")
        print(f"Size: {os.path.getsize(result)} bytes")
        # Check dimensions
        from PIL import Image
        img = Image.open(result)
        print(f"Dimensions: {img.size}")
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
