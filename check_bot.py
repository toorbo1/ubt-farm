import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

cmds = [
    "ls /opt/ubt-farm/bot*/",
    "head -50 /opt/ubt-farm/bot2/main.py | grep -i 'image_gen\\|builder\\|generate\\|scene'",
]

for cmd in cmds:
    print(f'=== {cmd} ===')
    _, stdout, _ = c.exec_command(cmd)
    data = stdout.read()
    with open('diag_bot.txt', 'wb') as f:
        f.write(data)
    with open('diag_bot.txt', 'r', encoding='utf-8', errors='replace') as f:
        print(f.read())
    print()

c.close()
