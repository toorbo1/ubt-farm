from google import genai
from google.genai import types
import os

KEYS = [
    ("key1", "AQ.Ab8RN6Is7YzkaELKqx1Hn-IR30pEPtcT5ias4EmkruinZzVMTA"),
    ("key2", "AQ.Ab8RN6L3Kik3-BPs394N1_-CyZD4m1o3g0qfDKTg_xfHrAMo3Q"),
]

os.makedirs("test_output", exist_ok=True)

for name, key in KEYS:
    print(f"\n=== {name} ===")
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents="Generate a pixel art image of a small black pixel cat with green eyes on a keyboard. 9:16 vertical.",
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"]
            ),
        )
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    out = f"test_output/{name}.jpg"
                    with open(out, "wb") as f:
                        f.write(part.inline_data.data)
                    print(f"  SUCCESS: {out} ({os.path.getsize(out)} bytes)")
    except Exception as e:
        err = str(e)
        if "429" in err:
            print(f"  429 QUOTA EXHAUSTED")
        elif "404" in err:
            print(f"  404 MODEL NOT FOUND")
        elif "403" in err:
            print(f"  403 FORBIDDEN")
        else:
            print(f"  ERROR: {err[:200]}")
