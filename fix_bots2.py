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
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors="replace")

# Fix ecosystem.config.js - remove generic "ubt-bot"
print("Uploading ecosystem.config.js...")
sftp.put("ecosystem.config.js", "/opt/ubt-farm/ecosystem.config.js")
sftp.close()

# Check .env
print("Checking .env tokens...")
out = run("cat /opt/ubt-farm/.env")
for line in out.split("\n"):
    line = line.strip()
    if "TELEGRAM_BOT_TOKEN" in line:
        val = line.split("=", 1)[1][:20] if "=" in line else ""
        print(f"  {line.split('=')[0]}={val}...")

# Kill all and restart
print("\nRestarting...")
run("pm2 delete all 2>/dev/null")
run("pm2 delete ubt-bot 2>/dev/null")
time.sleep(1)

run("cd /opt/ubt-farm && pm2 start ecosystem.config.js")
time.sleep(4)

# Status
out = run("pm2 status")
for line in out.split("\n"):
    if any(x in line.lower() for x in ["ubt", "online", "vpn", "id", "app", "─"]):
        print(line.encode("ascii", errors="replace").decode())

# Logs
print("\nBot 1 log (last 3 lines):")
out = run("tail -3 /opt/ubt-farm/logs/bot1-out.log")
for line in out.split("\n"):
    l = line.strip().encode("ascii", errors="replace").decode()
    if l: print(f"  {l}")

print("Bot 2 log (last 3 lines):")
out = run("tail -3 /opt/ubt-farm/logs/bot2-out.log")
for line in out.split("\n"):
    l = line.strip().encode("ascii", errors="replace").decode()
    if l: print(f"  {l}")

print("Bot 1 error log:")
out = run("tail -3 /opt/ubt-farm/logs/bot1-error.log")
for line in out.split("\n"):
    l = line.strip().encode("ascii", errors="replace").decode()
    if l: print(f"  {l}")

client.close()
print("\nDone!")
