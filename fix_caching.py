import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

# Get the step2 function to see its full code
_, stdout, _ = c.exec_command('sed -n "642,715p" /opt/ubt-farm/bot/handlers.py')
data = stdout.read()
with open('step2.txt', 'wb') as f:
    f.write(data)

_, stdout2, _ = c.exec_command('sed -n "577,640p" /opt/ubt-farm/bot/handlers.py')
data2 = stdout2.read()
with open('step1.txt', 'wb') as f:
    f.write(data2)

_, stdout3, _ = c.exec_command('sed -n "717,798p" /opt/ubt-farm/bot/handlers.py')
data3 = stdout3.read()
with open('step3.txt', 'wb') as f:
    f.write(data3)

c.close()

print('=== STEP 1 ===')
with open('step1.txt', 'r', encoding='utf-8', errors='replace') as f:
    print(f.read()[:1000])

print('\n=== STEP 2 ===')
with open('step2.txt', 'r', encoding='utf-8', errors='replace') as f:
    print(f.read()[:1500])

print('\n=== STEP 3 ===')
with open('step3.txt', 'r', encoding='utf-8', errors='replace') as f:
    print(f.read()[:1000])
