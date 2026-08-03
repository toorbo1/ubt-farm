import paramiko
import sys

LOCAL = r'C:\Users\User\Desktop\убт'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=15, banner_timeout=15)

sftp = c.open_sftp()
sftp.put(LOCAL + r'\bot\handlers.py', '/opt/ubt-farm/bot/handlers.py')
sftp.close()
print('handlers.py uploaded')

# Kill conflicting bots using bot tokens
stdin, stdout, stderr = c.exec_command("pkill -f 8760700962 2>/dev/null; pkill -f 8427880718 2>/dev/null; echo done")
print(stdout.read().decode('utf-8', errors='replace'))

stdin, stdout, stderr = c.exec_command('pm2 restart ubt-bot1 ubt-bot2 2>&1')
print(stdout.read().decode('utf-8', errors='replace'))

c.close()
print('Done')
