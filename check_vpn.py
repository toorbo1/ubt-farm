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

# Check VPN monitor status
print("=== PM2 STATUS ===")
out = run("pm2 status")
for l in out.split("\n"):
    l = l.encode("ascii", errors="replace").decode().strip()
    if l: print(l)

# Check port
print("\n=== PORT 8443 ===")
out = run("ss -tlnp | grep 8443 || echo NOT_LISTENING")
print(out.encode("ascii", errors="replace").decode().strip())

# Test with curl
print("\n=== CURL LOCALHOST ===")
out = run('curl -sk https://127.0.0.1:8443/api/stats -H "X-API-Key: ventura-api-key-2025" 2>&1')
print(out[:500].encode("ascii", errors="replace").decode())

print("\n=== CURL EXTERNAL ===")
out = run('curl -sk https://144.31.25.159:8443/api/stats -H "X-API-Key: ventura-api-key-2025" 2>&1')
print(out[:500].encode("ascii", errors="replace").decode())

# Check VPN errors in bot logs
print("\n=== VPN ERRORS IN BOT LOGS ===")
out = run("grep -i 'vpn\|error' /opt/ubt-farm/logs/bot1-error.log 2>/dev/null | tail -5 || echo NO_LOGS")
for l in out.split("\n"):
    l = l.encode("ascii", errors="replace").decode().strip()
    if l: print(l)

client.close()
