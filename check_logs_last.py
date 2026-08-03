import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)

# Check bot2 out log for image gen errors
stdin, stdout, stderr = client.exec_command(
    "tail -60 /opt/ubt-farm/logs/bot2-out.log 2>/dev/null | grep -i -E 'error|fail|fallback|AI#2' | tail -10"
)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print("=== Bot2 errors ===")
print(out[:2000])
print(err[:500])

# Also check the full recent logs
stdin, stdout, stderr = client.exec_command("tail -30 /opt/ubt-farm/logs/bot2-out.log 2>/dev/null")
full = stdout.read().decode("utf-8", errors="replace")
print("\n=== Bot2 recent full ===")
print(full[:2000])

# Check error log
stdin, stdout, stderr = client.exec_command("tail -20 /opt/ubt-farm/logs/bot2-error.log 2>/dev/null")
err_log = stdout.read().decode("utf-8", errors="replace")
if err_log.strip():
    print("\n=== Bot2 error log ===")
    print(err_log[:1000])

client.close()
