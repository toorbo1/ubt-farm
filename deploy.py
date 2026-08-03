"""Deploy updated files to server."""
import paramiko, time
LOCAL = r'C:\Users\User\Desktop\убт'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())

for i in range(3):
    try:
        c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)
        print('CONNECTED')
        sftp = c.open_sftp()

        files = [
            (LOCAL + r'\core\image_gen.py', '/opt/ubt-farm/core/image_gen.py'),
            (LOCAL + r'\core\video_ai.py', '/opt/ubt-farm/core/video_ai.py'),
            (LOCAL + r'\core\llm_client.py', '/opt/ubt-farm/core/llm_client.py'),
            (LOCAL + r'\video_engine\builder.py', '/opt/ubt-farm/video_engine/builder.py'),
            (LOCAL + r'\config\settings.py', '/opt/ubt-farm/config/settings.py'),
        ]
        for local, remote in files:
            sftp.put(local, remote)
            print(f'  OK: {remote}')
        sftp.close()

        stdin, stdout, stderr = c.exec_command(
            'cd /opt/ubt-farm && pip install google-genai 2>&1 | tail -3 && '
            'echo ===ENV=== && cat .env | grep GEMINI || true'
        )
        out = stdout.read().decode(errors='replace')
        err = stderr.read().decode(errors='replace')
        print('OUT:', out[:600])
        if err.strip():
            print('ERR:', err[:300])

        # Restart bots
        stdin2, stdout2, stderr2 = c.exec_command(
            'cd /opt/ubt-farm && pm2 restart ubt-bot1 ubt-bot2 2>&1'
        )
        print('RESTART:', stdout2.read().decode(errors='replace')[:200])

        c.close()
        print('DEPLOY SUCCESS')
        break
    except Exception as e:
        print(f'Attempt {i}: {e}')
        time.sleep(5)
