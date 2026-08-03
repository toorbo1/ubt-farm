import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)

# Check out log
stdin, stdout, _ = client.exec_command("tail -60 /opt/ubt-farm/logs/bot2-out.log 2>/dev/null")
out = stdout.read().decode("utf-8", errors="replace")
with open("log_out.txt", "w", encoding="utf-8") as f:
    f.write(out)

# Check error log
stdin, stdout, _ = client.exec_command("tail -40 /opt/ubt-farm/logs/bot2-error.log 2>/dev/null")
err = stdout.read().decode("utf-8", errors="replace")
with open("log_err.txt", "w", encoding="utf-8") as f:
    f.write(err)

# Check if ffmpeg exists
stdin, stdout, _ = client.exec_command("which ffmpeg 2>&1; ffmpeg -version 2>&1 | head -1")
ffmpeg = stdout.read().decode(errors="replace").strip()
with open("log_ffmpeg.txt", "w", encoding="utf-8") as f:
    f.write(ffmpeg)

client.close()
