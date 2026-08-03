import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

# Get the ConversationHandler setup and add_handler calls
_, stdout, _ = c.exec_command('grep -n "ConversationHandler\\|add_handler\\|CommandHandler\\|step1\\|step2\\|step3\\|farm_text\\|build\\|batch" /opt/ubt-farm/bot/handlers.py | head -50')
data = stdout.read()
with open('conv.txt', 'wb') as f:
    f.write(data)
c.close()

with open('conv.txt', 'r', encoding='utf-8', errors='replace') as f:
    print(f.read())
