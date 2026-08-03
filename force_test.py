import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

# Check bot uptime + trigger test generation
cmds = [
    'pm2 status | grep ubt-bot',
    'cd /opt/ubt-farm && python3 -c "from core.image_gen import get_image_generator; print(type(get_image_generator()).__name__)" 2>/dev/null',
]

for cmd in cmds:
    print(f'=== {cmd[:80]} ===')
    _, stdout, _ = c.exec_command(cmd)
    data = stdout.read()
    import re
    text = data.decode('utf-8', errors='replace')
    text = re.sub(r'[^\x20-\x7E\x0A\x0D\u0400-\u04FFa-zA-Z0-9.,:;!?()/-]', '', text)
    print(text[:500])
    print()

c.close()
