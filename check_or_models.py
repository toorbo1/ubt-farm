import asyncio, httpx, json, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEY = "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"

async def main():
    headers = {"Authorization": f"Bearer {KEY}"}
    async with httpx.AsyncClient(timeout=30) as c:
        # Get all available models
        r = await c.get("https://openrouter.ai/api/v1/models", headers=headers)
        if r.status_code == 200:
            data = r.json()
            models = data.get("data", [])
            print(f"Total models: {len(models)}")
            # Find image-related models
            img_models = [m for m in models if any(k in (m.get("id","") or "").lower() for k in ["flux", "stable-diffusion", "dall-e", "sdxl", "image", "gen"])]
            print(f"\nImage models ({len(img_models)}):")
            for m in sorted(img_models, key=lambda x: x["id"]):
                pricing = m.get("pricing", {})
                print(f"  {m['id']}")
                print(f"    Image? {'Y' if m.get('capabilities', {}).get('image') else 'N'}, Input: {m.get('capabilities',{}).get('input')}, Output: {m.get('capabilities',{}).get('output')}")
        else:
            print(f"Error: {r.status_code} {r.text[:500]}")

asyncio.run(main())
