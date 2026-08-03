import asyncio, httpx, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEY = "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"

async def main():
    headers = {"Authorization": f"Bearer {KEY}"}
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get("https://openrouter.ai/api/v1/models", headers=headers)
        if r.status_code == 200:
            data = r.json()
            models = data.get("data", [])
            # Search broadly for anything image-related
            for m in models:
                mid = m.get("id", "")
                desc = str(m.get("description", "")).lower()
                name = str(m.get("name", "")).lower()
                combined = f"{mid} {desc} {name}"
                if any(k in combined for k in ["image", "dall", "flux", "stable", "diffus", "sdxl", "pixel", "art", "draw"]):
                    print(f"  {m['id']}")
                    print(f"     Pricing: {m.get('pricing')}")
                    print(f"     Arch: {m.get('architecture',{})}")
            
            # Also dump all model IDs to file for analysis
            with open("or_models.txt", "w", encoding="utf-8") as f:
                for m in models:
                    f.write(f"{m['id']}\n")
            print(f"\nSaved all {len(models)} model IDs to or_models.txt")

asyncio.run(main())
