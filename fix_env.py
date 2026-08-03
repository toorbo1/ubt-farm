import paramiko

HOST = "144.31.25.159"
USER = "root"
PASSWORD = "BYAgu5iR5RgE0XuA"
REMOTE_DIR = "/opt/ubt-farm"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USER, PASSWORD, timeout=15)

sftp = client.open_sftp()

env_content = """TELEGRAM_BOT_TOKEN=8427880718:AAFIE85dNPEVW5HFIXmj7uvviK5ZExqV-mw
TELEGRAM_BOT_TOKEN_2=8760700962:AAFHtirhjGkDQMN7nC5VthqB0e3DU2Zatjo
LLM_API_KEY=
LLM_MODEL=deepseek-chat
TTS_ENGINE=edge
VPN_API_URL=https://144.31.25.159:8443
VPN_API_KEY=ventura-api-key-2025
"""

with sftp.open(f"{REMOTE_DIR}/.env", "w") as f:
    f.write(env_content)
sftp.close()

stdin, stdout, stderr = client.exec_command(f"cd {REMOTE_DIR} && pm2 restart ubt-bot1 ubt-bot2")
stdout.channel.recv_exit_status()

import time
time.sleep(3)

stdin, stdout, stderr = client.exec_command(f"cat {REMOTE_DIR}/logs/bot1-out.log 2>/dev/null | tail -5")
out = stdout.read().decode(errors="replace")
for line in out.split("\n"):
    line = line.encode("ascii", errors="replace").decode()
    print(line)

stdin, stdout, stderr = client.exec_command(f"cat {REMOTE_DIR}/logs/bot1-error.log 2>/dev/null | tail -5")
out = stdout.read().decode(errors="replace")
for line in out.split("\n"):
    line = line.encode("ascii", errors="replace").decode()
    print(line)

client.close()
print("[OK] .env updated and bots restarted")
