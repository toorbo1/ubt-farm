import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)

stdin, stdout, stderr = client.exec_command(
    "cd /opt/ubt-farm && pm2 start ecosystem.config.js --only ubt-bot1 && sleep 2 && "
    "pm2 start ecosystem.config.js --only ubt-bot2 && sleep 3 && pm2 status"
)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print("OUT:", out[-1500:])
print("ERR:", err[-500:])

# Check actual running
stdin, stdout, stderr = client.exec_command("pm2 status 2>&1 | tail -15")
print(stdout.read().decode("utf-8", errors="replace"))

client.close()
