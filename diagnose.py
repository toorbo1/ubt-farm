import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('144.31.25.159', 22, 'root', 'BYAgu5iR5RgE0XuA', timeout=30, banner_timeout=15)

cmds = [
    'grep -n "LLM_MODEL\\|llm_model\\|openrouter_image_model" /opt/ubt-farm/.env',
    'grep -n "SYSTEM_PROMPT\\|SCENE_PROMPT" /opt/ubt-farm/core/llm_client.py | head -5',
    'grep -n "def generate_scenes\\|def generate" /opt/ubt-farm/core/llm_client.py | head -10',
    'grep -n "get_image_generator\\|class.*Generator" /opt/ubt-farm/core/image_gen.py | head -20',
]

for cmd in cmds:
    print(f'=== {cmd} ===')
    _, stdout, _ = c.exec_command(cmd)
    data = stdout.read()
    with open('diag_temp.txt', 'wb') as f:
        f.write(data)
    with open('diag_temp.txt', 'r', encoding='utf-8', errors='replace') as f:
        print(f.read())
    print()

c.close()
