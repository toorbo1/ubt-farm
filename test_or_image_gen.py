import asyncio, httpx, json, sys, re
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEY = "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"
OUT = Path("output") / "test"
OUT.mkdir(parents=True, exist_ok=True)

async def test_gemini_image(model: str):
    print(f"\n--- {model} ---")
    headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    prompt = "Cinematic photorealistic portrait of a young woman sitting at a desk with a laptop, warm lighting, cozy room, ultra detailed, 4K, vertical 9:16 aspect ratio"
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": f"Generate an image: {prompt}. Return ONLY the image URL, no text."}
        ],
        "max_tokens": 4096,
    }
    
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
        print(f"HTTP {r.status_code}")
        if r.status_code != 200:
            print(f"Error: {r.text[:300]}")
            return
        
        data = r.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"Response length: {len(content)} chars")
        
        # Look for image URL or base64 in the response
        urls = re.findall(r'https?://[^\s"\'<>]+\.(?:png|jpg|jpeg|gif|webp)', content)
        if urls:
            print(f"Found URL: {urls[0][:80]}...")
            r2 = await c.get(urls[0])
            r2.raise_for_status()
            name = model.split("/")[-1].replace("-", "_")
            out = OUT / f"or_{name}.jpg"
            out.write_bytes(r2.content)
            print(f"Saved: {out.name} ({out.stat().st_size} bytes)")
            return
        
        # Check for base64 in markdown
        b64_match = re.search(r'data:image/(?:png|jpg|jpeg);base64,([A-Za-z0-9+/=]+)', content)
        if b64_match:
            import base64
            img_bytes = base64.b64decode(b64_match.group(1))
            out = OUT / f"or_{model.split('/')[-1]}.jpg"
            out.write_bytes(img_bytes)
            print(f"Saved from base64: {out.name} ({len(img_bytes)} bytes)")
            return
        
        # Check for base64 in JSON
        b64_json = re.search(r'"b64_json":\s*"([A-Za-z0-9+/=]+)"', content)
        if b64_json:
            import base64
            img_bytes = base64.b64decode(b64_json.group(1))
            out = OUT / "or_b64.jpg"
            out.write_bytes(img_bytes)
            print(f"Saved from b64_json: {out.name} ({len(img_bytes)} bytes)")
            return
        
        # Show a snippet to understand the format
        print(f"Content preview: {content[:500]}")

async def main():
    models = [
        "google/gemini-2.5-flash-image",
        "google/gemini-3.1-flash-image",
        "google/gemini-3.1-flash-lite-image",
        "openai/gpt-5-image-mini",
    ]
    for m in models:
        await test_gemini_image(m)

if __name__ == "__main__":
    asyncio.run(main())
