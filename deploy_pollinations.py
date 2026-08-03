import paramiko

LOCAL = r'C:\Users\User\Desktop\убт'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

sftp = c.open_sftp()
sftp.put(LOCAL + r'\core\image_gen.py', '/opt/ubt-farm/core/image_gen.py')
sftp.close()
print('image_gen.py uploaded')

_, stdout, _ = c.exec_command('pm2 restart ubt-bot1 ubt-bot2')
stdout.read()
print('Bots restarted')

c.close()
