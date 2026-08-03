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

# Test API endpoints
tests = [
    ('curl -sk https://127.0.0.1:8443/api/latest -H "X-API-Key: ventura-api-key-2025"', "/api/latest"),
    ('curl -sk https://127.0.0.1:8443/api/stats -H "X-API-Key: ventura-api-key-2025"', "/api/stats"),
]

for cmd, label in tests:
    out = run(cmd)
    print(f"=== {label} ===")
    content = out.encode("ascii", errors="replace").decode().strip()
    print(content[:500])
    print()

# Test bot's VPN fetch directly
print("=== Bot VPN test (python) ===")
cmd = "cd /opt/ubt-farm && venv/bin/python3 -c \"import asyncio; from bot.vpn_handlers import vpn_fetch_data; print(asyncio.run(vpn_fetch_data()))\""
out = run(cmd)
print(out[:500].encode("ascii", errors="replace").decode())

client.close()
