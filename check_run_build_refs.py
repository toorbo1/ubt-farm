import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)
sftp = client.open_sftp()

with sftp.open("/opt/ubt-farm/bot/handlers.py", "rb") as f:
    content = f.read().decode("utf-8")

# Find every reference to _run_build
for i, line in enumerate(content.split("\n"), 1):
    if "_run_build" in line:
        print(f"Line {i}: {line.strip().encode('ascii', errors='replace').decode()}")

sftp.close()
client.close()
