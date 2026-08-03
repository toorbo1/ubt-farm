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

time.sleep(2)

# Check logs
print("=== VPN Monitor Logs ===")
out = run("pm2 logs vpn-monitor --lines 10 --nostream 2>&1 | head -20")
for l in out.split("\n"):
    l = l.encode("ascii", errors="replace").decode().strip()
    if l: print(l)

# Check SSL
print("\n=== SSL Certs ===")
out = run("ls -la /root/vpn-monitor/ssl/ 2>/dev/null || echo NO_SSL_DIR")
print(out.encode("ascii", errors="replace").decode().strip())

# Try to start without SSL (HTTP mode for testing)
print("\n=== Test without SSL ===")
out = run('curl -k https://127.0.0.1:8443/api/stats -H "X-API-Key: ventura-api-key-2025" 2>&1 || echo FAILED')
print(out[:300].encode("ascii", errors="replace").decode().strip())

out = run('curl -k https://127.0.0.1:8443/ 2>&1 | head -5 || echo FAILED')
print(out[:300].encode("ascii", errors="replace").decode().strip())

# Check if port is now listening
out = run("ss -tlnp 2>/dev/null | grep -E '8443|8080' || echo NO_PORT")
print(f"\nPorts: {out.encode('ascii', errors='replace').decode().strip()}")

# Check what port vpn-monitor is actually using
out = run("ps aux | grep vpn-monitor | grep -v grep")
print(f"\nProcess: {out.encode('ascii', errors='replace').decode().strip()[:200]}")

client.close()
