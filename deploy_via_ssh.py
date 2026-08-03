"""
Deploy UBT Farm to 144.31.25.159 via SSH (paramiko).
Run: python deploy_via_ssh.py
"""
import os
import sys
import traceback
from pathlib import Path

import paramiko

HOST = "144.31.25.159"
USER = "root"
PASSWORD = "BYAgu5iR5RgE0XuA"
PORT = 22
REMOTE_DIR = "/opt/ubt-farm"

PROJECT_DIR = Path(__file__).resolve().parent

EXCLUDE_DIRS = {".git", "__pycache__", "venv", "node_modules", ".idea"}
EXCLUDE_EXTS = {".pyc", ".pyo"}
EXCLUDE_FILES = {".env"}


def should_exclude(path: Path, rel: str) -> bool:
    parts = rel.split(os.sep)
    for p in parts:
        if p in EXCLUDE_DIRS:
            return True
    if path.suffix in EXCLUDE_EXTS:
        return True
    if path.name in EXCLUDE_FILES:
        return True
    if path.suffix == ".mp4" and "output" in parts:
        return True
    return False


def safe_print(msg: str) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode())


safe_print("=" * 55)
safe_print("  UBT Farm - deploy to 144.31.25.159")
safe_print("=" * 55)

# 1. Connect
safe_print("\n[1/6] Connecting to server...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect(HOST, PORT, USER, PASSWORD, timeout=15)
    safe_print("  [OK] Connected")
except Exception as e:
    safe_print(f"  [FAIL] Connection error: {e}")
    sys.exit(1)

sftp = client.open_sftp()

try:
    # 2. Create directories
    safe_print("\n[2/6] Creating directories...")
    dirs = [
        REMOTE_DIR,
        f"{REMOTE_DIR}/bot",
        f"{REMOTE_DIR}/config",
        f"{REMOTE_DIR}/core",
        f"{REMOTE_DIR}/video_engine",
        f"{REMOTE_DIR}/uploader",
        f"{REMOTE_DIR}/uniqueizer",
        f"{REMOTE_DIR}/storage",
        f"{REMOTE_DIR}/assets",
        f"{REMOTE_DIR}/assets/backgrounds",
        f"{REMOTE_DIR}/assets/fonts",
        f"{REMOTE_DIR}/output",
        f"{REMOTE_DIR}/logs",
        f"{REMOTE_DIR}/profiles",
    ]
    for d in dirs:
        try:
            sftp.stat(d)
        except FileNotFoundError:
            sftp.mkdir(d)
            safe_print(f"  > Created {d}")
    safe_print("  [OK] Directories ready")

    # 3. Upload files
    safe_print("\n[3/6] Uploading files...")
    uploaded = 0
    for file_path in PROJECT_DIR.rglob("*"):
        if not file_path.is_file():
            continue
        rel = str(file_path.relative_to(PROJECT_DIR))
        if should_exclude(file_path, rel):
            continue
        remote_path = f"{REMOTE_DIR}/{rel.replace(os.sep, '/')}"
        try:
            sftp.put(str(file_path), remote_path)
            uploaded += 1
            if uploaded % 30 == 0:
                safe_print(f"  > Uploaded {uploaded} files...")
        except Exception as e:
            safe_print(f"  > ! {rel}: {e}")
    safe_print(f"  [OK] Uploaded {uploaded} files")

    # 4. Install dependencies
    safe_print("\n[4/6] Installing dependencies...")
    commands = [
        ("apt-get update -qq", "System update"),
        ("apt-get install -y -qq python3 python3-pip python3-venv ffmpeg curl > /dev/null 2>&1", "Packages"),
        ("command -v node || (curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1 && apt-get install -y -qq nodejs > /dev/null 2>&1)", "Node.js"),
        ("npm install -g pm2 > /dev/null 2>&1 || true", "PM2"),
        (f"cd {REMOTE_DIR} && python3 -m venv venv", "Python venv"),
        (f"cd {REMOTE_DIR} && venv/bin/pip install -q -U pip setuptools wheel", "Pip update"),
        (f"cd {REMOTE_DIR} && venv/bin/pip install -q -r requirements.txt", "Python deps"),
        (f"cd {REMOTE_DIR} && venv/bin/python3 -m playwright install chromium > /dev/null 2>&1", "Playwright"),
        (f"cd {REMOTE_DIR} && venv/bin/python3 -m playwright install-deps chromium > /dev/null 2>&1", "Playwright deps"),
    ]
    for cmd, label in commands:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=300)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code == 0:
            safe_print(f"  [OK] {label}")
        else:
            err = stderr.read().decode().strip()[:80]
            safe_print(f"  [OK] {label} (warn: {err})")

    # 5. PM2
    safe_print("\n[5/6] Configuring PM2...")
    pm2_config = f"""const path = require('path');
module.exports = {{
  apps: [
    {{
      name: "ubt-bot1",
      script: "{REMOTE_DIR}/bot/run_bot.py",
      interpreter: "{REMOTE_DIR}/venv/bin/python3",
      args: "--bot 1",
      cwd: "{REMOTE_DIR}",
      error_file: "{REMOTE_DIR}/logs/bot1-error.log",
      out_file: "{REMOTE_DIR}/logs/bot1-out.log",
      merge_logs: true,
      max_memory_restart: "500M",
      max_restarts: 10,
      restart_delay: 5000,
    }},
    {{
      name: "ubt-bot2",
      script: "{REMOTE_DIR}/bot/run_bot.py",
      interpreter: "{REMOTE_DIR}/venv/bin/python3",
      args: "--bot 2",
      cwd: "{REMOTE_DIR}",
      error_file: "{REMOTE_DIR}/logs/bot2-error.log",
      out_file: "{REMOTE_DIR}/logs/bot2-out.log",
      merge_logs: true,
      max_memory_restart: "500M",
      max_restarts: 10,
      restart_delay: 5000,
    }},
  ],
}};
"""
    with sftp.open(f"{REMOTE_DIR}/ecosystem.config.js", "w") as f:
        f.write(pm2_config)
    safe_print("  [OK] PM2 ecosystem uploaded")

    # Start via PM2
    pm2_cmds = [
        f"cd {REMOTE_DIR} && pm2 delete ubt-bot1 ubt-bot2 2>/dev/null; pm2 start ecosystem.config.js",
        f"cd {REMOTE_DIR} && pm2 save",
        "pm2 startup systemd -u root --hp /root 2>/dev/null || true",
    ]
    for cmd in pm2_cmds:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        stdout.channel.recv_exit_status()
        safe_print(f"  [OK] PM2: {cmd[:50]}...")

    # 6. Logrotate
    safe_print("\n[6/6] Configuring logrotate...")
    logrotate_conf = f"""{REMOTE_DIR}/logs/*.log {{
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}}
"""
    with sftp.open("/etc/logrotate.d/ubt-farm", "w") as f:
        f.write(logrotate_conf)
    safe_print("  [OK] Logrotate configured")

    # Final status
    safe_print("\n" + "=" * 55)
    safe_print("  Checking bot status...")
    stdin, stdout, stderr = client.exec_command("pm2 status")
    safe_print(stdout.read().decode())
    safe_print("  [DONE] Deploy complete!")
    safe_print("=" * 55)
    safe_print(f"  Bot 1: pm2 logs ubt-bot1 --lines 20")
    safe_print(f"  Bot 2: pm2 logs ubt-bot2 --lines 20")
    safe_print(f"  .env:  nano {REMOTE_DIR}/.env")

except Exception as e:
    safe_print(f"\n  [FAIL] Error: {e}")
    traceback.print_exc()

finally:
    sftp.close()
    client.close()
    safe_print("  SSH connection closed.")
