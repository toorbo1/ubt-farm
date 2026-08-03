import paramiko, sys
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)
_, stdout, _ = c.exec_command("pm2 status | grep ubt-bot")
data = stdout.read()
sys.stdout.buffer.write(data)
c.close()
