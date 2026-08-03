import asyncio, httpx, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEY = "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"

async def test(model: str):
    print(f"\n=== {model} ===")
    headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    prompt = "Generate a photorealistic image of a cat sitting on a desk with a laptop, cinematic lighting"
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": f"Create an image: {prompt}"}
        ],
    }
    
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
        print(f"HTTP {r.status_code}")
        # Print full response
        data = r.json()
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])

async def main():
    await test("google/gemini-2.5-flash-image")
    await test("openai/gpt-5-image-mini")

asyncio.run(main())
