import paramiko, re
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

ranges = [(295,310), (650,670), (725,750)]
for start, end in ranges:
    _, stdout, _ = c.exec_command(f"sed -n '{start},{end}p' /opt/ubt-farm/bot/handlers.py")
    data = stdout.read()
    with open(f'chk_{start}.txt', 'wb') as f:
        f.write(data)

c.close()

for start, end in ranges:
    print(f'=== Lines {start}-{end} ===')
    with open(f'chk_{start}.txt', 'r', encoding='utf-8', errors='replace') as f:
        text = re.sub(r'[^\x20-\x7E\x0A\x0D\u0400-\u04FFa-zA-Z0-9_.,:;!?()/@#\[\]\-]', '', f.read())
        print(text)
