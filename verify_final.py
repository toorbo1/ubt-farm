import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)
sftp = client.open_sftp()

# Check image_gen.py
with sftp.open("/opt/ubt-farm/core/image_gen.py", "rb") as f:
    img = f.read().decode("utf-8")
print(f"PollinationsImageGenerator: {'PollinationsImageGenerator' in img}")
print(f"get_image_generator returns Pollinations: {'return PollinationsImageGenerator()' in img}")

# Check video_ai.py  
with sftp.open("/opt/ubt-farm/core/video_ai.py", "rb") as f:
    vid = f.read().decode("utf-8")
print(f"get_img2video returns LocalKenBurns: {'return LocalKenBurnsGenerator()' in vid}")

# Check builder.py for ffmpeg fix
with sftp.open("/opt/ubt-farm/video_engine/builder.py", "rb") as f:
    bld = f.read().decode("utf-8")
print(f"ffmpeg path fix: {'srt_filter' in bld}")

# Check .env
with sftp.open("/opt/ubt-farm/.env", "rb") as f:
    env = f.read().decode("utf-8")
print(f"LLM key in env: {'sk-or-v1' in env}")
print(f"Pollinations not in env: {'pollinations' not in env}")

sftp.close()
client.close()
print("DONE")
