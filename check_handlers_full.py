import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

# Get all function defs in handlers.py
_, stdout, _ = c.exec_command('grep -n "^async def\\|^    async def\\|^def " /opt/ubt-farm/bot/handlers.py')
data = stdout.read()
with open('funcs.txt', 'wb') as f:
    f.write(data)

# Also check what commands the bot responds to
_, stdout2, _ = c.exec_command('grep -n "Application\\|add_handler\\|CommandHandler\\|MessageHandler" /opt/ubt-farm/bot/handlers.py | head -30')
data2 = stdout2.read()
with open('cmds.txt', 'wb') as f:
    f.write(data2)

c.close()

print('=== Functions in handlers.py ===')
with open('funcs.txt', 'r', encoding='utf-8', errors='replace') as f:
    print(f.read())

print('\n=== Handlers registered ===')
with open('cmds.txt', 'r', encoding='utf-8', errors='replace') as f:
    print(f.read())
