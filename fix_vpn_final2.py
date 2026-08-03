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
    raw = f.read()
content = raw.decode("utf-8")

# Find the HTTP redirect section
old_line = "http.createServer((req, res) => {"
new_code = """const httpServer = http.createServer((req, res) => {
  res.writeHead(301, { Location: 'https://' + req.headers.host + req.url });
  res.end();
});
httpServer.on('error', (err) => {
  console.log('HTTP server unavailable (port ' + PORT_HTTP + '): ' + err.message);
});
httpServer.listen(PORT_HTTP);"""

if old_line in content:
    # Find the full block from http.createServer to .listen(PORT_HTTP);
    start = content.find(old_line)
    end = content.find("}).listen(PORT_HTTP);", start)
    if end > start:
        end += len("}).listen(PORT_HTTP);")
        old_block = content[start:end]
        content = content.replace(old_block, new_code)
        print("Fixed HTTP server error handling!")
    else:
        print("Could not find end of HTTP block")
else:
    print("Could not find HTTP server code")

# Write back
sftp.open("/root/vpn-monitor/server.js", "wb").write(content.encode("utf-8"))
sftp.close()

# Restart
print("Restarting VPN Monitor...")
run("pm2 delete vpn-monitor 2>/dev/null")
time.sleep(1)

run("cd /root/vpn-monitor && PORT_HTTPS=8443 pm2 start server.js --name vpn-monitor --update-env 2>&1")
time.sleep(4)

# Check
out = run("ss -tlnp | grep 8443 || echo NOT_LISTENING")
print(f"Port 8443: {out[:100].encode('ascii', errors='replace').decode().strip()}")

out = run('curl -sk https://127.0.0.1:8443/api/stats -H "X-API-Key: ventura-api-key-2025" 2>&1')
print(f"API: {out[:300].encode('ascii', errors='replace').decode().strip()}")

out = run("pm2 status")
for l in out.split("\n"):
    l = l.encode("ascii", errors="replace").decode().strip()
    if any(x in l for x in ["ubt", "vpn", "online", "id", "-"]):
        print(l)

run("pm2 save")
client.close()
print("Done!")
