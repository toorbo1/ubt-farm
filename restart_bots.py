import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)
# Restart bots and suppress output
_, stdout, _ = c.exec_command('pm2 restart ubt-bot1 ubt-bot2 --log-date-format "HH:MM" > /dev/null 2>&1; echo DONE')
out = stdout.read().decode(errors='replace')
print(out.strip())
c.close()
