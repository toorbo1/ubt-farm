from google import genai
from google.genai import types
import os

KEYS = [
    ("key1", "AQ.Ab8RN6Is7YzkaELKqx1Hn-IR30pEPtcT5ias4EmkruinZzVMTA"),
    ("key2", "AQ.Ab8RN6L3Kik3-BPs394N1_-CyZD4m1o3g0qfDKTg_xfHrAMo3Q"),
]

MODELS = [
    "gemini-2.5-flash-image",
    "gemini-3.1-flash-image-preview",
    "gemini-3.1-flash-image",
    "gemini-3-pro-image-preview",
    "gemini-3.1-flash-lite-image",
]

os.makedirs("test_output", exist_ok=True)

for name, key in KEYS:
    print(f"\n=== {name} ===")
    for model in MODELS:
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=model,
                contents="Generate a pixel art image of a small black pixel cat. 9:16.",
                config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
            )
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                        out = f"test_output/{name}_{model.replace('.','_').replace('-','_')}.jpg"
                        with open(out, "wb") as f:
                            f.write(part.inline_data.data)
                        print(f"  [{model}] SUCCESS ({os.path.getsize(out)} bytes)")
        except Exception as e:
            err = str(e)
            if "429" in err:
                print(f"  [{model}] 429 QUOTA")
            elif "404" in err:
                print(f"  [{model}] 404")
            else:
                msg = err[:150]
                print(f"  [{model}] {msg}")
