import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)

# Check what's in /opt/ubt-farm
stdin, stdout, stderr = client.exec_command("ls -la /opt/ubt-farm/")
print(stdout.read().decode("utf-8", errors="replace"))

# Check pm2 config
stdin, stdout, stderr = client.exec_command("cat /opt/ubt-farm/ecosystem.config.js 2>/dev/null || ls /opt/ubt-farm/*.js 2>/dev/null || ls /opt/ubt-farm/*.json 2>/dev/null; echo 'DONE'")
print(stdout.read().decode("utf-8", errors="replace"))

# Check full directory tree
stdin, stdout, stderr = client.exec_command("find /opt/ubt-farm -name '*.py' -maxdepth 2 | sort")
print(stdout.read().decode("utf-8", errors="replace"))

client.close()
