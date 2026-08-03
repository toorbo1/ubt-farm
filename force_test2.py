import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

_, stdout, stderr = c.exec_command('cd /opt/ubt-farm && python3 -c "from core.image_gen import get_image_generator; print(type(get_image_generator()).__name__)"')
out = stdout.read()
err = stderr.read()
with open('ft_out.txt', 'wb') as f:
    f.write(out)
with open('ft_err.txt', 'wb') as f:
    f.write(err)

_, stdout2, _ = c.exec_command('which python3 && python3 --version')
vout = stdout2.read()
with open('ft_ver.txt', 'wb') as f:
    f.write(vout)

c.close()

with open('ft_out.txt', 'r') as f: print('OUT:', f.read().strip())
with open('ft_err.txt', 'r') as f: print('ERR:', f.read().strip()[:200])
with open('ft_ver.txt', 'r') as f: print('VER:', f.read().strip())
