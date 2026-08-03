import httpx, asyncio, os, time

PROMPTS = [
    "2D pixel art, 16-bit retro game style, a cute small black cat with glowing green eyes sitting on a giant keyboard, paws typing, pixel sparks flying from keys, dark room with neon cyan glow from monitors, 9:16 vertical pixel art",
    "2D pixel art, pixel cat standing on two legs pointing a paw at a giant pixel lock icon, night pixel city background with neon signs, cyberpunk, purple and pink colors, 9:16 vertical",
    "2D pixel art, black pixel cat sleeping curled up on a glowing laptop, warm amber light, cozy pixel room with plants and bookshelves, soft pixel shadows, pastel colors, 9:16 vertical",
]

async def test_pollinations():
    os.makedirs("test_output", exist_ok=True)
    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, prompt in enumerate(PROMPTS):
            from urllib.parse import quote
            url = f"https://image.pollinations.ai/prompt/{quote(prompt[:600])}?width=1080&height=1920&nologo=true&model=flux"
            print(f"\n[{i}] Image attempt 1...")
            for att in range(3):
                resp = await client.get(url, follow_redirects=True)
                print(f"  attempt {att}: HTTP {resp.status_code}, size={len(resp.content)}")
                if resp.status_code == 429:
                    print(f"  rate limited! body={resp.text[:200]}")
                    await asyncio.sleep(10*(att+1))
                    continue
                if resp.status_code == 200:
                    fname = f"test_output/pollinations_{i}.jpg"
                    with open(fname, "wb") as f:
                        f.write(resp.content)
                    print(f"  saved: {fname} ({len(resp.content)} bytes)")
                    break
                resp.raise_for_status()
            if i < len(PROMPTS) - 1:
                await asyncio.sleep(5)

asyncio.run(test_pollinations())
