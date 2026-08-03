import paramiko, os, time
from pathlib import Path

HOST, USER, PASSWORD = "144.31.25.159", "root", "BYAgu5iR5RgE0XuA"
REMOTE = "/opt/ubt-farm"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USER, PASSWORD, timeout=15)
sftp = client.open_sftp()

# Upload .env
with open(".env", "r", encoding="utf-8") as f:
    sftp.open(f"{REMOTE}/.env", "w").write(f.read())
print("env ok")

# Upload code
root = Path.cwd()
n = 0
for fp in root.rglob("*"):
    if not fp.is_file(): continue
    rel = str(fp.relative_to(root))
    parts = rel.split(os.sep)
    if any(p in parts for p in (".git", "__pycache__", "venv", "node_modules")): continue
    if fp.suffix in (".pyc", ".pyo", ".mp4") or fp.name == ".env": continue
    try:
        sftp.put(str(fp), f"{REMOTE}/{rel.replace(os.sep, '/')}")
        n += 1
    except: pass
print(f"code {n} files")

sftp.close()

# Clear cache
client.exec_command("find /opt/ubt-farm -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null")
client.exec_command("find /opt/ubt-farm -name '*.pyc' -delete 2>/dev/null")

# Restart
client.exec_command("cd /opt/ubt-farm && pm2 startOrReload ecosystem.config.js")
time.sleep(3)

stdin, stdout, _ = client.exec_command("pm2 status 2>&1 | grep -E 'ubt|online' | head -5")
print(stdout.read().decode("utf-8", errors="replace")[:200])
client.close()
print("done")
