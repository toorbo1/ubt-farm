import paramiko
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="cp1251", errors="replace")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)

commands = [
    "find /opt/ubt-farm -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; echo 'DONE_PYCACHE'",
    "find /opt/ubt-farm -name '*.pyc' -delete 2>/dev/null; echo 'DONE_PYC'",
    "pm2 delete ubt-bot1 ubt-bot2 2>/dev/null; echo 'DONE_DELETE'",
    "cd /opt/ubt-farm && pm2 start run_bot.py --name ubt-bot1 --interpreter /opt/ubt-farm/venv/bin/python3 -- --bot 1; echo 'DONE_START1'",
    "sleep 2; echo 'DONE_SLEEP'",
    "cd /opt/ubt-farm && pm2 start run_bot.py --name ubt-bot2 --interpreter /opt/ubt-farm/venv/bin/python3 -- --bot 2; echo 'DONE_START2'",
    "sleep 3; pm2 status; echo 'DONE_STATUS'",
]

for cmd in commands:
    print(f"> {cmd[:100]}")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out.strip():
        print(out.strip()[:300])
    if err.strip():
        print(f"ERR: {err.strip()[:200]}")
    time.sleep(0.5)

# Verify code
sftp = client.open_sftp()
files_to_check = [
    "/opt/ubt-farm/bot/handlers.py",
    "/opt/ubt-farm/core/llm_client.py",
    "/opt/ubt-farm/core/image_gen.py",
]
for path in files_to_check:
    with sftp.open(path, "rb") as f:
        raw = f.read()
    has_step1 = b"_step1_generate_text" in raw
    has_vpn = b"vpn \xd0\xb8 \xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb0\xd1\x82\xd0\xbd\xd0\xbe\xd1\x81\xd1\x82\xd1\x8c" in raw
    has_cat = b"\xd1\x87\xd0\xb5\xd1\x80\xd0\xbd\xd1\x8b\xd0\xb9 \xd0\xbf\xd0\xb8\xd0\xba\xd1\x81\xd0\xb5\xd0\xbb\xd1\x8c\xd0\xbd\xd1\x8b\xd0\xb9 \xd0\xba\xd0\xbe\xd1\x82\xd0\xb8\xd0\xba" in raw
    name = path.split("/")[-1]
    print(f"{name}: step1={has_step1}, vpn_key={has_vpn}, black_cat={has_cat}")

sftp.close()
client.close()
print("DONE")
