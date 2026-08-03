import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)
sftp = client.open_sftp()

with sftp.open("/opt/ubt-farm/bot/handlers.py", "rb") as f:
    content = f.read().decode("utf-8")

idx = content.find("async def handle_farm_text")
if idx >= 0:
    end = content.find("async def ", idx + 50)
    snippet = content[idx:end] if end > idx else content[idx:idx+2000]
    print(snippet.encode("ascii", errors="replace").decode())

sftp.close()
client.close()
