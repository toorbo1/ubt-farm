import asyncio, httpx, json, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEY = "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"

async def test_image_endpoint(model: str):
    print(f"\n--- Testing {model} ---")
    
    # Try /images/generations first
    headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "prompt": "test cat", "n": 1, "size": "1024x1024"}
    
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post("https://openrouter.ai/api/v1/images/generations", json=payload, headers=headers)
        print(f"  /images/generations: HTTP {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"    OK: {list(data.keys())}")
            if "data" in data:
                print(f"    Items: {len(data['data'])}")
            return
        else:
            body = r.text[:200]
            print(f"    Body: {body}")
        
        # Try /chat/completions
        payload2 = {
            "model": model,
            "messages": [{"role": "user", "content": "Generate an image of a cat"}],
            "max_tokens": 4096,
        }
        r2 = await c.post("https://openrouter.ai/api/v1/chat/completions", json=payload2, headers=headers)
        print(f"  /chat/completions: HTTP {r2.status_code}")
        if r2.status_code == 200:
            data = r2.json()
            print(f"    OK: {list(data.keys())}")
        else:
            print(f"    Body: {r2.text[:200]}")

async def test_different_sizes(model: str):
    print(f"\n--- Testing sizes for {model} ---")
    headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    sizes = ["1024x1024", "1024x1792", "896x1152", "1152x896", "768x1344", "1344x768"]
    async with httpx.AsyncClient(timeout=30) as c:
        for size in sizes:
            payload = {"model": model, "prompt": "test cat", "n": 1, "size": size}
            r = await c.post("https://openrouter.ai/api/v1/images/generations", json=payload, headers=headers)
            print(f"  size {size}: HTTP {r.status_code}")

async def main():
    models = [
        "stabilityai/stable-diffusion-3.5-large",
        "black-forest-labs/flux-dev",
        "black-forest-labs/flux-schnell",
        "stabilityai/sdxl",
        "openai/dall-e-3",
    ]
    for m in models:
        await test_image_endpoint(m)
    
    # Test sizes for the best model
    await test_different_sizes("black-forest-labs/flux-dev")

asyncio.run(main())
