import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

# Check for "фоновая" (fallback) in recent log
_, stdout, _ = c.exec_command('grep -c "фоновая\\|Gemini\\|All keys" /opt/ubt-farm/logs/bot2-out.log /opt/ubt-farm/logs/bot2-error.log 2>/dev/null')
data = stdout.read()
with open('fb_log.txt', 'wb') as f:
    f.write(data)

# Also check the actual generated files
_, stdout2, _ = c.exec_command('ls -la /opt/ubt-farm/output/scenes/ 2>/dev/null | tail -15')
data2 = stdout2.read()
with open('fb_files.txt', 'wb') as f:
    f.write(data2)

_, stdout3, _ = c.exec_command('ls -la /opt/ubt-farm/output/ubt_video_*.mp4 2>/dev/null | tail -5')
data3 = stdout3.read()
with open('fb_vids.txt', 'wb') as f:
    f.write(data3)

c.close()

print('=== Fallback hits ===')
with open('fb_log.txt', 'r') as f:
    print(f.read()[:500])

print('=== Scene files ===')
with open('fb_files.txt', 'r') as f:
    print(f.read()[:500])

print('=== Video files ===')
with open('fb_vids.txt', 'r') as f:
    print(f.read()[:500])
