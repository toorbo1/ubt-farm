"""
Fix and deploy: LLM + VPN fixes to server.
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

EXCLUDE = {".git", "__pycache__", "venv", "node_modules", ".idea"}
EXCLUDE_FILES = {".env"}

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USER, PASSWORD, timeout=15)
sftp = client.open_sftp()

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors="replace")

# Upload only changed files
files_to_upload = [
    "core/llm_client.py",
    "config/settings.py",
    ".env",
    "bot/vpn_handlers.py",
    "bot/handlers.py",
    "bot/keyboards.py",
    "bot/run_bot.py",
]

print("Uploading fixes...")
for rel in files_to_upload:
    local = PROJECT_DIR / rel
    if local.exists():
        remote = f"{REMOTE_DIR}/{rel}"
        sftp.put(str(local), remote)
        print(f"  [OK] {rel}")
    else:
        print(f"  [SKIP] {rel} not found")

sftp.close()

# Restart bots
print("\nRestarting bots...")
run("pm2 restart ubt-bot1 ubt-bot2 2>/dev/null")

import time
time.sleep(4)

# Check status
out = run("pm2 status")
for line in out.split("\n"):
    if "ubt" in line.lower() or "─" in line:
        print(line.encode("ascii", errors="replace").decode())

# Test VPN connection locally
print("\nTesting VPN API locally...")
out = run("curl -sk https://127.0.0.1:8443/api/stats -H 'X-API-Key: ventura-api-key-2025' 2>/dev/null || echo CURL_FAILED")
print(f"  Response: {out[:200].encode('ascii', errors='replace').decode()}")

client.close()
print("\nDone! Fixes deployed.")
