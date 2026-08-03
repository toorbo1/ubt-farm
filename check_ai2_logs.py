import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)

stdin, stdout, stderr = client.exec_command(
    "tail -80 /opt/ubt-farm/logs/bot2-out.log 2>/dev/null | grep -i -E 'AI#2|AI#3|AI#1|fallback|error|готово|готов|картин|фон' | tail -20"
)
out = stdout.read().decode("utf-8", errors="replace")
print(out[:2000])

print("\n=== FULL recent ===")
stdin2, stdout2, stderr2 = client.exec_command("tail -40 /opt/ubt-farm/logs/bot2-out.log 2>/dev/null")
full = stdout2.read().decode("utf-8", errors="replace")
print(full[:2000])

client.close()
