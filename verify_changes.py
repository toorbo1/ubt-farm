import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)
sftp = client.open_sftp()

# Check llm_client SCENE_PROMPT
with sftp.open("/opt/ubt-farm/core/llm_client.py", "rb") as f:
    raw = f.read().decode("utf-8")
no_pixel = "pixel art" not in raw
has_cinematic = "cinematic" in raw and "photorealistic" in raw
print(f"SCENE_PROMPT no pixel art: {no_pixel}, has cinematic: {has_cinematic}")

# Check image model
with sftp.open("/opt/ubt-farm/.env", "rb") as f:
    env = f.read().decode("utf-8")
has_sd = "stable-diffusion-3.5" in env
has_flux = "flux-schnell" in env
print(f"Model SD3.5: {has_sd}, flux-schnell: {has_flux}")

# Check image size
with sftp.open("/opt/ubt-farm/core/image_gen.py", "rb") as f:
    raw = f.read().decode("utf-8")
size_ok = "1024x1024" in raw
print(f"Image size 1024x1024: {size_ok}")

sftp.close()
client.close()
print("done")
