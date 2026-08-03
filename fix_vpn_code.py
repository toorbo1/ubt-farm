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
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return out + err

# Read server.js
print("Reading server.js...")
with sftp.open("/root/vpn-monitor/server.js", "rb") as f:
    raw = f.read()
content = raw.decode("utf-8")

# Print the relevant section around line 45-55
lines = content.split("\n")
print("Lines 44-52:")
for i, line in enumerate(lines[43:52], 44):
    print(f"  {i}: {line.rstrip()}")

# Fix: add error handler to HTTP server
old = """// Redirect HTTP \u2192 HTTPS
http.createServer((req, res) => {
  res.writeHead(301, { Location: `https://${req.headers.host}${req.url}` });
  res.end();
}).listen(PORT_HTTP);"""

new = """// Redirect HTTP \u2192 HTTPS
const httpServer = http.createServer((req, res) => {
  res.writeHead(301, { Location: `https://${req.headers.host}${req.url}` });
  res.end();
});
httpServer.on('error', (err) => {
  console.log('HTTP server unavailable (port ' + PORT_HTTP + '): ' + err.message);
});
httpServer.listen(PORT_HTTP);"""

if old in content:
    content = content.replace(old, new)
    print("\nFixed! Writing server.js...")
    sftp.open("/root/vpn-monitor/server.js", "w").write(content.encode("utf-8"))
    print("Done writing.")
else:
    print("\nCould not find exact match. Let me try alternative...")
    old2 = "http.createServer((req, res) => {"
    new2 = "const httpServer = http.createServer((req, res) => {"
    old3 = "}).listen(PORT_HTTP);"
    new3 = "});\nhttpServer.on('error', (err) => console.log('HTTP port ' + PORT_HTTP + ': ' + err.message));\nhttpServer.listen(PORT_HTTP);"
    
    if old2 in content and old3 in content:
        content = content.replace(old2, new2)
        content = content.replace("}).listen(PORT_HTTP);", new3)
        sftp.open("/root/vpn-monitor/server.js", "w").write(content.encode("utf-8"))
        print("Fixed via alternative method.")
    else:
        print("Could not fix - unknown code structure")

sftp.close()

# Kill old and restart
print("\nRestarting VPN Monitor...")
run("pm2 delete vpn-monitor 2>/dev/null")
time.sleep(1)

run("cd /root/vpn-monitor && PORT_HTTPS=8443 pm2 start server.js --name vpn-monitor --update-env 2>&1")
time.sleep(3)

# Check
out = run("ss -tlnp | grep 8443 || echo NOT_LISTENING")
print(f"\nPort 8443: {out.encode('ascii', errors='replace').decode().strip()[:100]}")

out = run('curl -sk https://127.0.0.1:8443/api/stats -H "X-API-Key: ventura-api-key-2025" 2>&1')
print(f"API: {out[:300].encode('ascii', errors='replace').decode().strip()}")

# Status
out = run("pm2 status")
for l in out.split("\n"):
    l = l.encode("ascii", errors="replace").decode().strip()
    if any(x in l for x in ["ubt", "vpn", "online", "id", "─"]):
        print(l)

run("pm2 save")
client.close()
print("\nDone!")
