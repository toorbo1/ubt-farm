import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

_, stdout, _ = c.exec_command("grep -n 'builder = VideoBuilder()' /opt/ubt-farm/bot/handlers.py")
data = stdout.read()
with open('builder_lines.txt', 'wb') as f:
    f.write(data)
c.close()

with open('builder_lines.txt', 'r', encoding='utf-8', errors='replace') as f:
    print(f.read())
