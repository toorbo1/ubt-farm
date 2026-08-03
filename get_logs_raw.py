import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)

# Get bot2 out log and write to local file
stdin, stdout, stderr = client.exec_command("tail -60 /opt/ubt-farm/logs/bot2-out.log 2>/dev/null")
with open("server_logs.txt", "w", encoding="utf-8") as f:
    f.write(stdout.read().decode("utf-8", errors="replace"))

# Also error log
stdin, stdout, stderr = client.exec_command("tail -30 /opt/ubt-farm/logs/bot2-error.log 2>/dev/null")
with open("server_errors.txt", "w", encoding="utf-8") as f:
    f.write(stdout.read().decode("utf-8", errors="replace"))

# Get bot1 logs too
stdin, stdout, stderr = client.exec_command("tail -40 /opt/ubt-farm/logs/bot1-out.log 2>/dev/null")
with open("server_bot1_logs.txt", "w", encoding="utf-8") as f:
    f.write(stdout.read().decode("utf-8", errors="replace"))

print("logs saved")
client.close()
