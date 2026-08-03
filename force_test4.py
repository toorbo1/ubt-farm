import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

sftp = c.open_sftp()
with sftp.open('/tmp/test_gen.py', 'w') as f:
    f.write("""import sys
sys.path.insert(0, '/opt/ubt-farm')
from core.image_gen import get_image_generator
g = get_image_generator()
print(type(g).__name__)
""")
sftp.close()

_, stdout, stderr = c.exec_command('cd /opt/ubt-farm && ./venv/bin/python3 /tmp/test_gen.py')
data = stdout.read()
err = stderr.read()
with open('ft_result.txt', 'wb') as f:
    f.write(data)
with open('ft_err2.txt', 'wb') as f:
    f.write(err)
c.close()

with open('ft_result.txt', 'r') as f:
    print('OUTPUT:', f.read().strip())
with open('ft_err2.txt', 'r') as f:
    err_content = f.read().strip()
    if err_content:
        print('STDERR:', err_content[:500])
    else:
        print('No stderr')
