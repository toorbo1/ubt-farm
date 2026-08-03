import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

cmds = [
    "find /opt/ubt-farm -name '*.py' -path '*/bot*/*' | head -20",
    "grep -rn 'image_gen\\|builder\\|LocalFallback\\|Pollinations' /opt/ubt-farm/bot*/ 2>/dev/null | head -20",
]

for cmd in cmds:
    print(f'=== {cmd} ===')
    _, stdout, _ = c.exec_command(cmd)
    data = stdout.read()
    with open('struc.txt', 'wb') as f:
        f.write(data)
    with open('struc.txt', 'r', encoding='utf-8', errors='replace') as f:
        print(f.read())
    print()

c.close()
