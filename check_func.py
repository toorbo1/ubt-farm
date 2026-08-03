import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)
# Get lines around get_image_generator function
_, stdout, _ = c.exec_command("awk '/def get_image_generator/,/^[^ ]/' /opt/ubt-farm/core/image_gen.py")
data = stdout.read()
with open('chk.txt', 'wb') as f:
    f.write(data)
c.close()
with open('chk.txt', 'r', encoding='utf-8') as f:
    print(f.read())
