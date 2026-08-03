import paramiko, time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)

# Clear cache, restart via ecosystem config
cmds = [
    "find /opt/ubt-farm -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; echo 'a'",
    "find /opt/ubt-farm -name '*.pyc' -delete 2>/dev/null; echo 'b'",
    "cd /opt/ubt-farm && pm2 startOrReload ecosystem.config.js 2>&1; echo 'c'",
    "sleep 4; echo 'd'",
    "pm2 status 2>&1 | grep -E 'ubt|online|offline' | head -5; echo 'e'",
]
for cmd in cmds:
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    print(f"{cmd[:60]} -> {out.strip()[:200]}")

# Verify key code on server
sftp = client.open_sftp()
with sftp.open("/opt/ubt-farm/bot/handlers.py", "rb") as f:
    raw = f.read()
print(f"step1: {b'_step1_generate_text' in raw}, run_build: {b'_run_build' in raw}")

with sftp.open("/opt/ubt-farm/core/image_gen.py", "rb") as f:
    raw = f.read()
print(f"cat_fallback: {b'black' in raw and b'cat' in raw}")

sftp.close()
client.close()
