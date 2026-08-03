import asyncio, httpx, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FAL_KEY = "fe1f6926-b892-4b68-b2cd-5e92d1822ea7:2673aa1399b34ed7462ada50eacf6dfc"
OUT = Path("output") / "test"
OUT.mkdir(parents=True, exist_ok=True)

async def test_fal_image(model: str, prompt: str, size: str = "1024x1024"):
    print(f"\n--- fal.ai {model} ---")
    headers = {"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"}
    
    async with httpx.AsyncClient(timeout=120) as c:
        # Submit
        r = await c.post(f"https://fal.run/{model}", json={"prompt": prompt, "image_size": size}, headers=headers)
        print(f"HTTP {r.status_code}")
        if r.status_code != 200:
            print(f"Body: {r.text[:300]}")
            return
        
        data = r.json()
        # Check for synchronous response or need to poll
        if "images" in data:
            img_url = data["images"][0]["url"]
            print(f"Got image URL: {img_url[:80]}...")
            r2 = await c.get(img_url)
            r2.raise_for_status()
            out = OUT / f"fal_{model.split('/')[-1]}.jpg"
            out.write_bytes(r2.content)
            print(f"Saved: {out.name} ({out.stat().st_size} bytes)")
        elif "status_url" in data or "response_url" in data:
            url = data.get("response_url") or data.get("status_url")
            print(f"Async, polling: {url[:80]}...")
            while True:
                await asyncio.sleep(3)
                s = await c.get(url, headers=headers)
                if s.status_code == 404:
                    continue
                s.raise_for_status()
                result = s.json()
                status = result.get("status")
                if status == "COMPLETED":
                    img_url = result.get("images", [{}])[0].get("url", "")
                    if not img_url:
                        img_url = result.get("image", {}).get("url", "")
                    print(f"Got image URL: {img_url[:80]}...")
                    r2 = await c.get(img_url)
                    r2.raise_for_status()
                    out = OUT / "fal_async.jpg"
                    out.write_bytes(r2.content)
                    print(f"Saved: {out.name} ({out.stat().st_size} bytes)")
                    return
                elif status in ("FAILED", "ERROR"):
                    print(f"Failed: {result}")
                    return
                print(f"  Status: {status}")
        else:
            print(f"Unexpected response: {json.dumps(data, indent=2)[:300]}")

async def main():
    models = [
        ("fal-ai/flux/schnell", "Cinematic shot of a young woman using a laptop in a cozy room, warm lighting, photorealistic, 8K"),
        ("fal-ai/flux/dev", "Cinematic shot of a young woman using a laptop in a cozy room, warm lighting, photorealistic, 8K"),
        ("fal-ai/stable-diffusion-v3", "Cinematic shot of a young woman using a laptop in a cozy room, warm lighting, photorealistic, 8K"),
    ]
    for model, prompt in models:
        await test_fal_image(model, prompt)

if __name__ == "__main__":
    import json
    asyncio.run(main())
