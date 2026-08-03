"""
Быстрое обновление кода ботов на сервере.
"""
import os
import sys
from pathlib import Path

import paramiko

HOST = "144.31.25.159"
USER = "root"
PASSWORD = "BYAgu5iR5RgE0XuA"
REMOTE_DIR = "/opt/ubt-farm"
PROJECT_DIR = Path(__file__).resolve().parent

EXCLUDE_DIRS = {".git", "__pycache__", "venv", "node_modules", ".idea"}
EXCLUDE_EXTS = {".pyc", ".pyo"}
EXCLUDE_FILES = {".env"}

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USER, PASSWORD, timeout=15)
sftp = client.open_sftp()

print("Uploading updated files...")
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

# Restart bots
print("Restarting bots...")
stdin, stdout, stderr = client.exec_command(
    f"cd {REMOTE_DIR} && pm2 restart ubt-bot1 ubt-bot2"
)
stdout.channel.recv_exit_status()

# Check status
stdin, stdout, stderr = client.exec_command("pm2 status")
out = stdout.read().decode(errors="replace")
for line in out.split("\n"):
    line = line.encode("ascii", errors="replace").decode()
    if "ubt" in line.lower() or "id" in line.lower() or "─" in line:
        print(line)

client.close()
print("Done!")
