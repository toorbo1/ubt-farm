import paramiko
import time

HOST = "144.31.25.159"
USER = "root"
PASSWORD = "BYAgu5iR5RgE0XuA"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USER, PASSWORD, timeout=15)
sftp = client.open_sftp()

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
    return stdout.read().decode(errors="replace")

# Read server.js
print("Reading server.js...")
with sftp.open("/root/vpn-monitor/server.js", "rb") as f:
    content = f.read().decode("utf-8")

# Add API key auth to /api/latest and /api/stats
# 1. Create a combined auth middleware
old_auth_func = """function auth(req, res, next) {
  if (req.session && req.session.ok) return next();
  return res.redirect('/login');
}"""

new_auth_func = """function auth(req, res, next) {
  if (req.session && req.session.ok) return next();
  if (req.headers['x-api-key'] === API_KEY) return next();
  return res.redirect('/login');
}"""

if old_auth_func in content:
    content = content.replace(old_auth_func, new_auth_func)
    print("Fixed auth middleware!")
else:
    print("Could not find auth function")

# Write back
sftp.open("/root/vpn-monitor/server.js", "wb").write(content.encode("utf-8"))
sftp.close()

# Restart VPN Monitor
print("Restarting VPN Monitor...")
run("pm2 restart vpn-monitor --update-env 2>/dev/null")
time.sleep(3)

# Test API
out = run('curl -sk https://127.0.0.1:8443/api/stats -H "X-API-Key: ventura-api-key-2025" 2>&1')
print(f"\nStats API: {out[:300].encode('ascii', errors='replace').decode().strip()}")

out = run('curl -sk https://127.0.0.1:8443/api/latest -H "X-API-Key: ventura-api-key-2025" 2>&1')
print(f"Latest API: {out[:500].encode('ascii', errors='replace').decode().strip()}")

# Test bot VPN module
print("\n=== Bot vpn_fetch_data test ===")
out = run("cd /opt/ubt-farm && venv/bin/python3 -c \"import asyncio; from bot.vpn_handlers import vpn_fetch_data; d = asyncio.run(vpn_fetch_data()); print(f'Got {len(d)} servers'); print(d[:2] if d else 'EMPTY')\" 2>&1")
for l in out.split("\n"):
    l = l.encode("ascii", errors="replace").decode().strip()
    if l: print(f"  {l[:200]}")

client.close()
print("\nDone!")
