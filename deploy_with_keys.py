"""
Deploy code + update .env with OpenRouter key, then restart bots.
"""
import paramiko
import time

HOST = "144.31.25.159"
USER = "root"
PASSWORD = "BYAgu5iR5RgE0XuA"
REMOTE_DIR = "/opt/ubt-farm"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USER, PASSWORD, timeout=15)
sftp = client.open_sftp()

# 1. Read local .env and update server .env
with open(".env", "r", encoding="utf-8") as f:
    local_env = f.read()

with sftp.open(f"{REMOTE_DIR}/.env", "w") as f:
    f.write(local_env)

print("Updated .env on server")

# 2. Upload code files (same as deploy_update.py)
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
EXCLUDE_DIRS = {".git", "__pycache__", "venv", "node_modules", ".idea"}
EXCLUDE_EXTS = {".pyc", ".pyo"}
EXCLUDE_FILES = {".env"}  # still exclude .env from the bulk upload since we already wrote it

uploaded = 0
for file_path in PROJECT_DIR.rglob("*"):
    if not file_path.is_file():
        continue
    rel = str(file_path.relative_to(PROJECT_DIR))
    parts = rel.split(os.sep)
    if any(p in EXCLUDE_DIRS for p in parts):
        continue
    if file_path.suffix in EXCLUDE_EXTS or file_path.name in EXCLUDE_FILES:
        continue
    if file_path.suffix == ".mp4":
        continue
    remote_path = f"{REMOTE_DIR}/{rel.replace(os.sep, '/')}"
    try:
        sftp.put(str(file_path), remote_path)
        uploaded += 1
    except Exception as e:
        print(f"  ! {rel}: {e}")

print(f"Uploaded {uploaded} files")
sftp.close()

# 3. Clear caches and restart
cmds = [
    "find /opt/ubt-farm -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null",
    "find /opt/ubt-farm -name '*.pyc' -delete 2>/dev/null",
    "cd /opt/ubt-farm && pm2 startOrReload ecosystem.config.js 2>&1",
]
for cmd in cmds:
    stdin, stdout, stderr = client.exec_command(cmd)
    stdout.channel.recv_exit_status()

time.sleep(5)

stdin, stdout, stderr = client.exec_command(
    "pm2 status 2>&1 | grep -E 'ubt-bot|online|offline|stopped'"
)
status = stdout.read().decode("utf-8", errors="replace")
print("PM2 status:", status[:300] if status.strip() else "check manually")

# Verify key is set
stdin, stdout, stderr = client.exec_command(
    "grep -c LLM_API_KEY /opt/ubt-farm/.env && "
    "grep LLM_API_KEY /opt/ubt-farm/.env | head -1 | cut -c1-30"
)
print(stdout.read().decode("utf-8", errors="replace"))

client.close()
print("Done!")
