import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

# Download handlers.py
sftp = c.open_sftp()
sftp.get('/opt/ubt-farm/bot/handlers.py', 'handlers_backup.py')

# Read and modify
with open('handlers_backup.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add cache clearing at the start of _step2_generate_images and _step3_generate_video
# And also in _run_build, _run_batch

# 1. Fix _run_build - add scenes cleanup before build
old1 = "async def _run_build("
new1 = "async def _run_build("
# The build() already has rmtree, so it's fine

# 2. Fix _step2_generate_images - add cache clear
old2 = '''async def _step2_generate_images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    builder = VideoBuilder()'''

new2 = '''async def _step2_generate_images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    builder = VideoBuilder()
    import shutil
    if builder.scenes_dir.exists():
        shutil.rmtree(builder.scenes_dir)
    builder.scenes_dir.mkdir(parents=True, exist_ok=True)'''

code = code.replace(old2, new2)

# 3. Fix _step3_generate_video - add cache clear
old3 = '''async def _step3_generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    builder = VideoBuilder()'''

new3 = '''async def _step3_generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    builder = VideoBuilder()
    import shutil
    if builder.scenes_dir.exists():
        shutil.rmtree(builder.scenes_dir)
    builder.scenes_dir.mkdir(parents=True, exist_ok=True)'''

code = code.replace(old3, new3)

# Also add to _run_batch for safety
old4 = '''async def _run_batch(update: Update, context: ContextTypes.DEFAULT_TYPE, count: int) -> None:
    builder = VideoBuilder()'''

new4 = '''async def _run_batch(update: Update, context: ContextTypes.DEFAULT_TYPE, count: int) -> None:
    builder = VideoBuilder()
    import shutil
    if builder.scenes_dir.exists():
        shutil.rmtree(builder.scenes_dir)
    builder.scenes_dir.mkdir(parents=True, exist_ok=True)'''

code = code.replace(old4, new4)

# Write back
with open('handlers_backup.py', 'w', encoding='utf-8') as f:
    f.write(code)

# Upload
sftp.put('handlers_backup.py', '/opt/ubt-farm/bot/handlers.py')
sftp.close()
print('PATCHED: handlers.py uploaded')

# Restart bots
_, stdout, _ = c.exec_command('pm2 restart ubt-bot1 ubt-bot2')
stdout.read()
print('BOTS RESTARTED')

# Clear all old files
_, stdout2, _ = c.exec_command('rm -rf /opt/ubt-farm/output/scenes && rm -f /opt/ubt-farm/output/ubt_video_*.mp4')
stdout2.read()
print('CACHE CLEARED')

c.close()
print('DONE')
