import paramiko, time

LOCAL = r'C:\Users\User\Desktop\убт'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())

for i in range(3):
    try:
        c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)
        print('CONNECTED')
        sftp = c.open_sftp()
        sftp.put(LOCAL + r'\core\image_gen.py', '/opt/ubt-farm/core/image_gen.py')
        print('  OK: image_gen.py')
        # Also update .env with both keys
        stdin, stdout, stderr = c.exec_command(
            'grep -q GEMINI_API_KEYS /opt/ubt-farm/.env && '
            'sed -i "s|GEMINI_API_KEYS=.*|GEMINI_API_KEYS=AQ.Ab8RN6Is7YzkaELKqx1Hn-IR30pEPtcT5ias4EmkruinZzVMTA,AQ.Ab8RN6L3Kik3-BPs394N1_-CyZD4m1o3g0qfDKTg_xfHrAMo3Q|" /opt/ubt-farm/.env || '
            'echo "GEMINI_API_KEYS=AQ.Ab8RN6Is7YzkaELKqx1Hn-IR30pEPtcT5ias4EmkruinZzVMTA,AQ.Ab8RN6L3Kik3-BPs394N1_-CyZD4m1o3g0qfDKTg_xfHrAMo3Q" >> /opt/ubt-farm/.env'
        )
        stdout.read()
        err = stderr.read().decode(errors='replace')
        if err.strip():
            print('  ENV ERR:', err[:100])
        else:
            print('  OK: .env updated')
        sftp.close()

        # Install google-genai if needed + restart bots
        _, stdout2, _ = c.exec_command(
            'cd /opt/ubt-farm && ./venv/bin/pip install google-genai -q 2>&1 | tail -1'
        )
        pip_out = stdout2.read().decode(errors='replace').strip()
        print('  PIP:', pip_out[:100] if pip_out else 'OK')

        _, stdout3, _ = c.exec_command('pm2 restart ubt-bot1 ubt-bot2')
        stdout3.read()
        print('  BOTS RESTARTED')

        c.close()
        print('DEPLOY SUCCESS')
        break
    except Exception as e:
        print(f'Attempt {i}: {e}')
        time.sleep(5)
