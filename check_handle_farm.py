import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)
sftp = client.open_sftp()

with sftp.open("/opt/ubt-farm/bot/handlers.py", "rb") as f:
    content = f.read().decode("utf-8")

# Find the topic handling code
idx = content.find("if text in topic_map")
if idx >= 0:
    snippet = content[idx:idx+400]
    print(snippet.encode("ascii", errors="replace").decode())
    print("\n---")
    has_step1 = "_step1_generate_text" in snippet
    has_run_build = "_run_build" in snippet
    print(f"Calls _step1_generate_text: {has_step1}")
    print(f"Calls _run_build: {has_run_build}")
else:
    print("NOT FOUND")

sftp.close()
client.close()
