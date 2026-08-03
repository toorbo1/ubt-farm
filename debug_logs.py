import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)

# Check both bot out logs for recent pipeline activity
for bot_id in [1, 2]:
    print(f"\n=== Bot {bot_id} recent logs ===")
    stdin, stdout, stderr = client.exec_command(
        f"tail -30 /opt/ubt-farm/logs/bot{bot_id}-out.log 2>/dev/null | head -30"
    )
    out = stdout.read().decode(errors="replace")
    safe = out.encode("ascii", errors="replace").decode()
    print(safe[-2000:])

# Check error logs
print("\n=== Error logs ===")
stdin, stdout, stderr = client.exec_command(
    "cat /opt/ubt-farm/logs/bot1-error.log /opt/ubt-farm/logs/bot2-error.log 2>/dev/null | grep -i -E 'error|traceback|exception' | tail -10"
)
out = stdout.read().decode(errors="replace")
safe = out.encode("ascii", errors="replace").decode()
print(safe or "No errors found")

client.close()
