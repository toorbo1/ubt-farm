import paramiko, re
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=15, banner_timeout=10)

_, stdout, _ = c.exec_command('echo rmtree count: $(grep -c rmtree /opt/ubt-farm/bot/handlers.py); echo scenes: $(ls /opt/ubt-farm/output/scenes 2>/dev/null | wc -l); echo vids: $(ls /opt/ubt-farm/output/ubt_video_*.mp4 2>/dev/null | wc -l)')
data = stdout.read()
c.close()
with open('fq.txt', 'wb') as f:
    f.write(data)
with open('fq.txt', 'r', encoding='utf-8', errors='replace') as f:
    print(f.read())
