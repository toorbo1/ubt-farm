import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

cmds = [
    'grep "get_image_generator" /opt/ubt-farm/core/image_gen.py',
    'grep "class LocalFallbackGenerator" /opt/ubt-farm/core/image_gen.py',
    'wc -l /opt/ubt-farm/core/image_gen.py',
    'grep GEMINI_API_KEYS /opt/ubt-farm/.env',
    'pm2 status | head -8',
]

for cmd in cmds:
    _, stdout, _ = c.exec_command(cmd)
    out = stdout.read().decode(errors='replace')
    print(f'$ {cmd}')
    print(out[:200])
    print()

c.close()
