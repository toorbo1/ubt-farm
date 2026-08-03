import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)
_, stdout, _ = c.exec_command('head -20 /opt/ubt-farm/core/llm_client.py')
data = stdout.read()
with open('check_llm.txt', 'wb') as f:
    f.write(data)
c.close()
with open('check_llm.txt', 'r', encoding='utf-8') as f:
    print(f.read())
