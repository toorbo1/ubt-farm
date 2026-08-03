import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

_, stdout, _ = c.exec_command('grep -n "pollinations\\|Pollinations\\|gen.pollinations\\|get_image_generator\\|LocalFallback\\|GeminiImage\\|image_gen" /opt/ubt-farm/bot/handlers.py')
data = stdout.read()
with open('handler_grep.txt', 'wb') as f:
    f.write(data)
c.close()
with open('handler_grep.txt', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()
    import re
    text = re.sub(r'[^\x20-\x7E\x0A\x0D\u0400-\u04FFa-zA-Z0-9_,.:;!?()/\-\'\"\[\]]', '', text)
    print(text)
