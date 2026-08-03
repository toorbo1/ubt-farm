import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

# Check latest log entries
_, stdout, _ = c.exec_command('tail -80 /opt/ubt-farm/logs/bot2-out.log 2>/dev/null || tail -80 /opt/ubt-farm/logs/bot2.log 2>/dev/null || echo "no logs"')
data = stdout.read()
with open('server_logs.txt', 'wb') as f:
    f.write(data)

_, stdout2, _ = c.exec_command('ls -la /opt/ubt-farm/logs/ 2>/dev/null || echo "no logs dir"')
data2 = stdout2.read()
with open('server_logs2.txt', 'wb') as f:
    f.write(data2)

c.close()

with open('server_logs2.txt', 'r', encoding='utf-8', errors='replace') as f:
    print('=== Logs dir ===')
    print(f.read())

with open('server_logs.txt', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()
    import re
    ascii_content = re.sub(r'[^\x20-\x7E\x0A\x0D\u0400-\u04FF]', '?', content[-2000:])
    print('=== Last log lines ===')
    print(ascii_content)

# Also check error log for tracebacks  
with open('errlog.txt', 'r') as f:
    err = f.read()
    # Find tracebacks
    import re
    tracebacks = re.findall(r'Traceback.*?(?=\n\n|\Z)', err, re.DOTALL)
    for tb in tracebacks[-5:]:
        print('=== ERROR TRACEBACK ===')
        print(tb[:500])
