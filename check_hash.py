import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)
# Check if hash-based generate exists
_, stdout, _ = c.exec_command("grep 'hashlib.md5' /opt/ubt-farm/core/image_gen.py")
data = stdout.read()
with open('check_hash.txt', 'wb') as f:
    f.write(data)
c.close()
with open('check_hash.txt', 'r', encoding='utf-8') as f:
    print(f.read() or 'NOT FOUND')
