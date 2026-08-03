import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)

sftp = client.open_sftp()

# Check .env
with sftp.open("/opt/ubt-farm/.env", "rb") as f:
    env = f.read().decode("utf-8")
has_openrouter = "sk-or-v1" in env
has_openrouter_model = "gpt-4o-mini" in env or "flux" in env
print(f"OpenRouter key in .env: {has_openrouter}")
print(f"Models set: {has_openrouter_model}")

# Check settings.py
with sftp.open("/opt/ubt-farm/config/settings.py", "rb") as f:
    raw = f.read().decode("utf-8")
has_image_model = "openrouter_image_model" in raw
print(f"OpenRouterImageModel in settings: {has_image_model}")

# Check image_gen.py
with sftp.open("/opt/ubt-farm/core/image_gen.py", "rb") as f:
    raw = f.read().decode("utf-8")
has_or_gen = "OpenRouterImageGenerator" in raw
print(f"OpenRouterImageGenerator in image_gen: {has_or_gen}")

# Check bots running
stdin, stdout, _ = client.exec_command("pm2 status 2>&1 | grep -c 'online'")
online = stdout.read().decode().strip()
print(f"Online processes: {online}")

# Check LLM key is set in env
stdin, stdout, _ = client.exec_command("grep LLM_API_KEY /opt/ubt-farm/.env | head -1 | grep -c sk-or")
has_key = stdout.read().decode().strip()
print(f"LLM key ends with f0a: {has_key == '1'}")

sftp.close()
client.close()
