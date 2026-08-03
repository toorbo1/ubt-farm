import paramiko, re

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

sftp = c.open_sftp()
sftp.get('/opt/ubt-farm/bot/handlers.py', 'handlers_v2.py')
sftp.close()

with open('handlers_v2.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add rmtree before every `builder = VideoBuilder()` except the first (in _run_build which already cleans)
# Lines: 299 (_run_batch - already patched), 584 (step1 - text only, no images), 
#        661 (_step2_generate_images), 739 (_step3_generate_video)

# Patch step2: line 661
old2 = '''    builder = VideoBuilder()\n    try:\n        image_paths = []'''
new2 = '''    builder = VideoBuilder()\n    import shutil\n    if builder.scenes_dir.exists():\n        shutil.rmtree(builder.scenes_dir)\n    builder.scenes_dir.mkdir(parents=True, exist_ok=True)\n    try:\n        image_paths = []'''

if old2 in code:
    code = code.replace(old2, new2)
    print('PATCH 2 APPLIED')
else:
    print('PATCH 2 NOT FOUND')

# Patch step3: line 739
old3 = '''    builder = VideoBuilder()\n    try:\n        # Generate scene videos from images'''
new3 = '''    builder = VideoBuilder()\n    import shutil\n    if builder.scenes_dir.exists():\n        shutil.rmtree(builder.scenes_dir)\n    builder.scenes_dir.mkdir(parents=True, exist_ok=True)\n    try:\n        # Generate scene videos from images'''

if old3 in code:
    code = code.replace(old3, new3)
    print('PATCH 3 APPLIED')
else:
    print('PATCH 3 NOT FOUND')
    # Try alternate matching
    old3b = '''    builder = VideoBuilder()\n    try:\n        scene_videos = []'''
    if old3b in code:
        code = code.replace(old3b, new3b := '''    builder = VideoBuilder()\n    import shutil\n    if builder.scenes_dir.exists():\n        shutil.rmtree(builder.scenes_dir)\n    builder.scenes_dir.mkdir(parents=True, exist_ok=True)\n    try:\n        scene_videos = []''')
        print('PATCH 3B APPLIED')

# Write and upload
with open('handlers_v2.py', 'w', encoding='utf-8') as f:
    f.write(code)

sftp = c.open_sftp()
sftp.put('handlers_v2.py', '/opt/ubt-farm/bot/handlers.py')
sftp.close()

# Verify
_, stdout, _ = c.exec_command("grep -c 'rmtree' /opt/ubt-farm/bot/handlers.py")
count = stdout.read().decode(errors='replace').strip()
print(f'rmtree count in handlers.py: {count}')

_, stdout2, _ = c.exec_command('pm2 restart ubt-bot1 ubt-bot2')
stdout2.read()
print('BOTS RESTARTED')

_, stdout3, _ = c.exec_command('rm -rf /opt/ubt-farm/output/scenes && rm -f /opt/ubt-farm/output/ubt_video_*.mp4')
stdout3.read()
print('CACHE CLEARED')

c.close()
