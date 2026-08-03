import paramiko, re
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

# Check patches applied
_, stdout, _ = c.exec_command("grep -n 'rmtree\\|scenes_dir' /opt/ubt-farm/bot/handlers.py")
data = stdout.read()
with open('verify_patch.txt', 'wb') as f:
    f.write(data)

# Check output dirs
_, stdout2, _ = c.exec_command('ls /opt/ubt-farm/output/ 2>/dev/null')
data2 = stdout2.read()
with open('verify_out.txt', 'wb') as f:
    f.write(data2)

c.close()

print('=== rmtree in handlers.py ===')
with open('verify_patch.txt', 'r', encoding='utf-8', errors='replace') as f:
    text = re.sub(r'[^\x20-\x7E\x0A\x0D\u0400-\u04FFa-zA-Z0-9_.,:;!?()/\-]', '', f.read())
    print(text)

print('\n=== Output dir ===')
with open('verify_out.txt', 'r', encoding='utf-8', errors='replace') as f:
    print(f.read() or '(empty - cache cleared)')
