import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

# Get last 100 lines of error log
_, stdout, _ = c.exec_command('tail -100 /opt/ubt-farm/logs/bot2-error.log')
data = stdout.read()

# Check if there are any tracebacks
_, stdout2, _ = c.exec_command('grep -c "Traceback\\|Error\\|Exception" /opt/ubt-farm/logs/bot2-error.log 2>/dev/null || echo "0"')
count = stdout2.read().decode(errors='replace').strip()

_, stdout3, _ = c.exec_command('grep -c "Pollinations\\|LocalFallback\\|Gemini\\|429\\|quota\\|rate.limit" /opt/ubt-farm/logs/bot2-error.log 2>/dev/null || echo "0"')
count2 = stdout3.read().decode(errors='replace').strip()

c.close()

print(f'Tracebacks/Errors: {count}')
print(f'API/rate issues: {count2}')

import re
text = data.decode('utf-8', errors='replace')
text = re.sub(r'[^\x20-\x7E\x0A\x0D\u0400-\u04FF]', '?', text)
print('=== LAST 100 LINES OF ERROR LOG ===')
print(text)
