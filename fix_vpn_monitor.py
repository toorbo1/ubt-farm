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

# Check if vpn-monitor files exist
print("=== Checking VPN Monitor files ===")
out = run("ls -la /root/vpn-monitor/server.js 2>/dev/null || ls -la /root/vpn-monitor/ 2>/dev/null || echo FILES_NOT_FOUND")
print(out.encode("ascii", errors="replace").decode().strip())

out = run("ls -la /opt/ubt-farm/../vpn-monitor/ 2>/dev/null || echo NOT_IN_OPT")
print(out.encode("ascii", errors="replace").decode().strip())

# Try to find server.js
out = run("find / -name server.js -not -path '*/node_modules/*' 2>/dev/null | head -5")
for l in out.split("\n"):
    l = l.strip().encode("ascii", errors="replace").decode()
    if l: print(f"  Found: {l}")

# Restart vpn-monitor from its original location
print("\n=== Restarting VPN Monitor ===")
# Check setup.sh for the original path
out = run("cat /root/vpn-monitor/setup.sh 2>/dev/null | grep APP_DIR || echo NO_SETUP")
print(out.encode("ascii", errors="replace").decode().strip())

# Try common locations
for path in ["/root/vpn-monitor", "/opt/vpn-monitor", "/root/vpn-monitor/server"]:
    out = run(f"ls {path}/server.js 2>/dev/null && echo FOUND || true")
    if "FOUND" in out:
        print(f"  Found at: {path}")
        out = run(f"cd {path} && pm2 start server.js --name vpn-monitor 2>&1 || echo FAILED")
        print(f"  Start: {out[:200].encode('ascii', errors='replace').decode()}")
        break

# Final status
print("\n=== Final PM2 Status ===")
out = run("pm2 status")
for l in out.split("\n"):
    l = l.encode("ascii", errors="replace").decode().strip()
    if l: print(l)

# Test VPN API
print("\n=== Testing VPN API ===")
out = run('curl -sk https://127.0.0.1:8443/api/stats -H "X-API-Key: ventura-api-key-2025" 2>&1 || echo FAILED')
print(out[:300].encode("ascii", errors="replace").decode())

client.close()
