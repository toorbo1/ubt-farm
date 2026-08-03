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

# Delete broken instance
run("pm2 delete vpn-monitor 2>/dev/null")
time.sleep(1)

# Start with correct env vars from setup.sh
print("Starting VPN Monitor with correct ports...")
cmd = (
    "cd /root/vpn-monitor && "
    "PORT_HTTPS=8443 PORT_HTTP=8080 "
    "ADMIN_USER=admin ADMIN_PASS=ventura2025 "
    "API_KEY=ventura-api-key-2025 "
    "pm2 start server.js --name vpn-monitor --update-env 2>&1"
)
out = run(cmd)
for l in out.split("\n"):
    l = l.encode("ascii", errors="replace").decode().strip()
    if l: print(f"  {l}")

time.sleep(3)

# Check if listening
out = run("ss -tlnp | grep -E '8443|8080' || echo NOT_LISTENING")
print(f"\nPorts: {out.encode('ascii', errors='replace').decode().strip()[:200]}")

# Test API
out = run('curl -sk https://127.0.0.1:8443/api/stats -H "X-API-Key: ventura-api-key-2025" 2>&1')
print(f"\nAPI response: {out[:300].encode('ascii', errors='replace').decode().strip()}")

# Status
print("\n=== PM2 Status ===")
out = run("pm2 status")
for l in out.split("\n"):
    l = l.encode("ascii", errors="replace").decode().strip()
    if any(x in l for x in ["ubt", "vpn", "online", "id", "─"]):
        print(l)

# Save PM2 config
run("pm2 save")

client.close()
print("\nDone!")
