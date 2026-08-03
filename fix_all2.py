import paramiko, time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)

cmds = [
    "find /opt/ubt-farm -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; echo 'ok'",
    "find /opt/ubt-farm -name '*.pyc' -delete 2>/dev/null; echo 'ok'",
    "cd /opt/ubt-farm && pm2 startOrReload ecosystem.config.js 2>&1; echo 'ok'",
    "sleep 5; echo 'ok'",
    "pm2 status 2>&1 | grep -E 'ubt|online|offline'; echo 'ok'",
]
for cmd in cmds:
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    if "error" in out.lower() or "err" in out.lower():
        print(f"CMD FAILED: {cmd[:60]}")

sftp = client.open_sftp()
with sftp.open("/opt/ubt-farm/bot/handlers.py", "rb") as f:
    raw = f.read()
print(f"step1={b'_step1_generate_text' in raw} run_build={b'_run_build' in raw}")
with sftp.open("/opt/ubt-farm/core/image_gen.py", "rb") as f:
    raw = f.read()
print(f"cat={b'black' in raw and b'cat' in raw} pixel={b'pixel' in raw}")
with sftp.open("/opt/ubt-farm/core/llm_client.py", "rb") as f:
    raw = f.read()
print(f"vpn_lower={b'vpn \xd0\xb8' in raw} cat_prompt={b'\xd1\x87\xd0\xb5\xd1\x80\xd0\xbd\xd1\x8b\xd0\xb9 \xd0\xbf\xd0\xb8\xd0\xba\xd1\x81\xd0\xb5\xd0\xbb\xd1\x8c\xd0\xbd\xd1\x8b\xd0\xb9 \xd0\xba\xd0\xbe\xd1\x82' in raw}")
sftp.close()
client.close()
print("done")
