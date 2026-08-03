import asyncio, httpx, json, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEY = "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"

async def main():
    headers = {"Authorization": f"Bearer {KEY}"}
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get("https://openrouter.ai/api/v1/models", headers=headers)
        if r.status_code == 200:
            data = r.json()
            models = data.get("data", [])
            # Search all models for various keywords
            for keyword in ["flux", "sd3", "stable-diffusion", "dall", "sdxl", "pika", "runway", "gen-3", "cog", "kling", "stability"]:
                found = [m["id"] for m in models if keyword.lower() in (m.get("id","") or "").lower()]
                if found:
                    print(f"{keyword}: {found}")
            
            # Also check what the first 20 models look like
            print(f"\nFirst 30 models:")
            for m in models[:30]:
                print(f"  {m['id']}")

asyncio.run(main())
