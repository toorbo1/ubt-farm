import asyncio, httpx, base64
from pathlib import Path

OUT = Path("output") / "test"
OUT.mkdir(parents=True, exist_ok=True)

async def test_pollinations():
    """Pollinations.ai - completely free, no API key needed"""
    print("\n=== Pollinations.ai (FREE) ===")
    prompt = "Cinematic vertical shot of a young woman working on a laptop at a desk, warm lighting, photorealistic, ultra detailed, 9:16 portrait"
    url = f"https://image.pollinations.ai/prompt/{httpx.AsyncClient().build_request('GET', '').url.copy_with(path='/').join(prompt)}"
    # Actually let me use the simpler URL format
    url = "https://image.pollinations.ai/prompt/" + prompt.replace(" ", "%20") + "?width=1080&height=1920&nologo=true"
    
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.get(url)
        print(f"HTTP {r.status_code}, size: {len(r.content)} bytes")
        if r.status_code == 200 and len(r.content) > 5000:
            out = OUT / "pollinations_test.jpg"
            out.write_bytes(r.content)
            print(f"Saved: {out.name}")
            return True
        else:
            print(f"Failed or too small: {r.text[:200]}")
            return False

async def test_huggingface():
    """Hugging Face free inference API"""
    print("\n=== Hugging Face (FREE) ===")
    # Try without API key first (free tier)
    prompt = "Cinematic vertical shot of a young woman working on a laptop at a desk, warm lighting, photorealistic, 9:16 portrait"
    
    # Using FLUX.1-schnell - fast and decent
    models = [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/stable-diffusion-3.5-large",
    ]
    
    for model in models:
        print(f"  Model: {model}")
        api_url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {}  # No key for free tier (rate limited)
        payload = {"inputs": prompt, "parameters": {"target_size": {"width": 1080, "height": 1920}}}
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(api_url, json=payload, headers=headers)
            if r.status_code == 200 and len(r.content) > 5000:
                model_name = model.split("/")[-1]
                out = OUT / f"hf_{model_name}.jpg"
                out.write_bytes(r.content)
                print(f"  OK: {out.name} ({len(r.content)} bytes)")
                return True
            elif r.status_code == 503:
                print(f"  Model loading (try again later): {r.text[:100]}")
            else:
                print(f"  HTTP {r.status_code}: {r.text[:100]}")
    return False

async def test_hf_with_key():
    """Hugging Face with free API key from hf.co/join"""
    print("\n=== Hugging Face (no key, rate limited) ===")
    prompt = "Cinematic portrait of a woman at a desk with laptop, photorealistic"
    
    # Use FLUX schnell - very fast
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(
            "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell",
            json={"inputs": prompt, "parameters": {"guidance_scale": 3.5, "num_inference_steps": 4}},
        )
        print(f"HTTP {r.status_code}, size: {len(r.content)}")
        if r.status_code == 200 and len(r.content) > 5000:
            out = OUT / "hf_flux_schnell.jpg"
            out.write_bytes(r.content)
            print(f"OK: {out.name}")
            return True
        else:
            print(f"Response: {r.text[:200]}")
            return False

async def main():
    await test_pollinations()
    await test_hf_with_key()

if __name__ == "__main__":
    asyncio.run(main())
