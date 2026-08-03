import asyncio, os
from core.image_gen import LocalFallbackGenerator

gen = LocalFallbackGenerator()

async def test():
    prompts = [
        '2D pixel art, black cat sitting on glowing keyboard, neon tech room, cyberpunk',
        '2D pixel art, black cat curled up on laptop, warm cozy room, bookshelves',
        '2D pixel art, black cat on rooftop looking at stars, night city background',
        '2D pixel art, black cat walking in pixel park with trees and flowers',
        '2D pixel art, black cat by window in pixel city street view',
    ]
    os.makedirs('test_output', exist_ok=True)
    for i, p in enumerate(prompts):
        f = f'test_output/fallback_{i}.jpg'
        await gen.generate(p, f)
        from PIL import Image
        img = Image.open(f)
        print(f'Image {i}: {img.size}, file={os.path.getsize(f)} bytes')

asyncio.run(test())
