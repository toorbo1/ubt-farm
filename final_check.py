import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

checks = [
    "grep -c 'rmtree' /opt/ubt-farm/bot/handlers.py",
    "grep -c 'VideoBuilder' /opt/ubt-farm/bot/handlers.py",
    "ls /opt/ubt-farm/output/scenes 2>/dev/null | wc -l",
    "ls /opt/ubt-farm/output/ubt_video_*.mp4 2>/dev/null | wc -l",
    "pm2 status | grep ubt-bot | awk '{print $2, $14}'",
]

for cmd in checks:
    _, stdout, _ = c.exec_command(cmd)
    data = stdout.read()
    with open('final_chk.txt', 'ab') as f:
        f.write(b'=== ' + cmd.encode()[:60] + b' ===\n' + data + b'\n')

c.close()

with open('final_chk.txt', 'r', encoding='utf-8', errors='replace') as f:
    import re
    text = re.sub(r'[^\x20-\x7E\x0A\x0D\u0400-\u04FFa-zA-Z0-9_.,:;!?()/@%#\[\]\-]', '', f.read())
    print(text)
