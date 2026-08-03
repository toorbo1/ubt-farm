import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

# Check what get_image_generator returns
_, stdout, _ = c.exec_command("grep -A 5 'def get_image_generator' /opt/ubt-farm/core/image_gen.py")
data = stdout.read()
with open('emergency.txt', 'wb') as f:
    f.write(data)

# Also check if LocalFallbackGenerator class exists
_, stdout2, _ = c.exec_command("grep 'class LocalFallbackGenerator' /opt/ubt-farm/core/image_gen.py")
data2 = stdout2.read()
with open('emergency2.txt', 'wb') as f:
    f.write(data2)

c.close()

with open('emergency.txt', 'r', encoding='utf-8') as f:
    print('=== get_image_generator ===')
    print(f.read())
with open('emergency2.txt', 'r', encoding='utf-8') as f:
    print('=== LocalFallbackGenerator ===')
    print(f.read())
