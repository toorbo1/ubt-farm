import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)

stdin, stdout, stderr = client.exec_command("tail -50 /opt/ubt-farm/logs/bot2-out.log 2>/dev/null")
with open("deploy_log.txt", "w", encoding="utf-8") as f:
    f.write(stdout.read().decode("utf-8", errors="replace"))

client.close()
