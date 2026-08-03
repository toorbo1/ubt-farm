import paramiko, re
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)
_, stdout, _ = c.exec_command("cat /opt/ubt-farm/.env | grep -v '^#' | grep -v '^$'")
data = stdout.read()
with open('env_out.txt', 'wb') as f:
    f.write(data)
c.close()
with open('env_out.txt', 'r', encoding='utf-8', errors='replace') as f:
    text = re.sub(r'[^\x20-\x7E\x0A\x0D\u0400-\u04FFa-zA-Z0-9_=.,:/@\-]', '', f.read())
    print(text)
