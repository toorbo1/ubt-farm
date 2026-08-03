import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

# Clear scenes + restart bots
cmds = [
    'rm -rf /opt/ubt-farm/output/scenes',
    'rm -f /opt/ubt-farm/output/ubt_video_*.mp4',
    'pm2 delete ubt-bot1 ubt-bot2',
    'cd /opt/ubt-farm && pm2 start bot2/run_bot.py --interpreter ./venv/bin/python3 --name ubt-bot1',
    'cd /opt/ubt-farm && pm2 start bot2/run_bot.py --interpreter ./venv/bin/python3 --name ubt-bot2',
    'pm2 status | grep ubt-bot',
]

for cmd in cmds:
    _, stdout, _ = c.exec_command(cmd)
    d = stdout.read()
    with open('rc_out.txt', 'ab') as f:
        f.write(b'=== ' + cmd.encode() + b' ===\n' + d + b'\n')

c.close()

with open('rc_out.txt', 'r', encoding='utf-8', errors='replace') as f:
    import re
    text = re.sub(r'[^\x20-\x7E\x0A\x0D\u0400-\u04FFa-zA-Z0-9_.,:;!?()\[\]/@\-]', '', f.read())
    print(text)
