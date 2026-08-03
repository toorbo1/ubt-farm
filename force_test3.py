import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

# Write a test script to server and run it
sftp = c.open_sftp()
with sftp.open('/tmp/test_gen.py', 'w') as f:
    f.write("""import sys
sys.path.insert(0, '/opt/ubt-farm')
from core.image_gen import get_image_generator
g = get_image_generator()
print(type(g).__name__)
""")
sftp.close()

    _, stdout, _ = c.exec_command('cd /opt/ubt-farm && ./venv/bin/python3 /tmp/test_gen.py')
data = stdout.read()
with open('ft_result.txt', 'wb') as f:
    f.write(data)

_, stderr2, _ = c.exec_command('cd /opt/ubt-farm && ./venv/bin/python3 /tmp/test_gen.py 2>&1')
data2 = stderr2.read()
with open('ft_err2.txt', 'wb') as f:
    f.write(data2)

c.close()

with open('ft_result.txt', 'r') as f:
    print('OUTPUT:', f.read().strip())
with open('ft_err2.txt', 'r') as f:
    content = f.read().strip()
    if content:
        print('STDERR:', content[:500])
    else:
        print('No stderr')
