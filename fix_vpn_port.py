import time
import paramiko

HOST = "144.31.25.159"
USER = "root"
PASSWORD = "BYAgu5iR5RgE0XuA"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USER, PASSWORD, timeout=15)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return out + err

# Find what's using port 8443
print("=== Port 8443 ===")
out = run("ss -tlnp | grep 8443 || fuser 8443/tcp 2>/dev/null || echo NOT_FOUND")
print(out.encode("ascii", errors="replace").decode().strip())

out = run("lsof -i :8443 2>/dev/null || echo NO_LSOF")
print(out.encode("ascii", errors="replace").decode().strip())

# Kill anything on 8443
print("\n=== Killing port 8443 ===")
out = run("fuser -k 8443/tcp 2>/dev/null; sleep 1; echo DONE")
print(out.encode("ascii", errors="replace").decode().strip())

# Delete old PM2 process
print("\n=== Cleaning PM2 ===")
out = run("pm2 delete vpn-monitor 2>/dev/null; echo CLEANED")
print(out.encode("ascii", errors="replace").decode().strip())

# Start fresh
print("\n=== Starting VPN Monitor ===")
out = run("cd /root/vpn-monitor && pm2 start server.js --name vpn-monitor 2>&1")
for l in out.split("\n"):
    l = l.encode("ascii", errors="replace").decode().strip()
    if l: print(l)

time.sleep(3)

# Check if it's listening
out = run("ss -tlnp | grep 8443 || echo STILL_NOT_LISTENING")
print(f"\nPort check: {out.encode('ascii', errors='replace').decode().strip()[:200]}")

# Test API
print("\n=== Testing API ===")
out = run('curl -sk https://127.0.0.1:8443/api/stats -H "X-API-Key: ventura-api-key-2025" 2>&1')
print(out[:500].encode("ascii", errors="replace").decode().strip())

# Final status
print("\n=== PM2 Status ===")
out = run("pm2 status")
for l in out.split("\n"):
    l = l.encode("ascii", errors="replace").decode().strip()
    if any(x in l for x in ["ubt", "vpn", "online", "id", "─"]):
        print(l)

client.close()
