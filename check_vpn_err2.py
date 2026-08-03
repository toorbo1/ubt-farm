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

print("=== PM2 Logs ===")
out = run("pm2 logs vpn-monitor --lines 15 --nostream 2>&1")
for l in out.split("\n"):
    l = l.encode("ascii", errors="replace").decode().strip()
    if l: print(l)

# Try starting directly to see error
print("\n=== Direct test ===")
out = run("cd /root/vpn-monitor && PORT_HTTPS=8443 PORT_HTTP=8080 node -e \"require('./server.js')\" 2>&1 | head -20 || true")
for l in out.split("\n"):
    l = l.encode("ascii", errors="replace").decode().strip()
    if l: print(l)

client.close()
