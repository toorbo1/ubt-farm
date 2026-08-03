import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)

sftp = client.open_sftp()

with sftp.open("/opt/ubt-farm/core/image_gen.py", "rb") as f:
    raw = f.read().decode("utf-8")

has_pollinations = "PollinationsImageGenerator" in raw
has_return_pollinations = "return PollinationsImageGenerator()" in raw
has_local_fallback = "LocalFallbackGenerator" in raw
print(f"PollinationsImageGenerator: {has_pollinations}")
print(f"get_image_generator returns Pollinations: {has_return_pollinations}")
print(f"LocalFallbackGenerator exists: {has_local_fallback}")

sftp.close()
client.close()
