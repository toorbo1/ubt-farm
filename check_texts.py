import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)
sftp = client.open_sftp()

with sftp.open("/opt/ubt-farm/core/llm_client.py", "rb") as f:
    content = f.read().decode("utf-8")

# Find texts_pool and _default_scenes
idx = content.find("texts_pool")
if idx >= 0:
    snippet = content[idx:idx+500]
    print("=== texts_pool (first 500 chars) ===")
    print(snippet.encode("ascii", errors="replace").decode())

# Check if vpn и приватность key exists as lowercase
idx2 = content.find('vpn и приватность')
if idx2 >= 0:
    print("\n=== Found 'vpn и приватность' at", idx2, "===")
    print(content[max(0,idx2-100):idx2+200].encode("ascii", errors="replace").decode())

# Check _default_scenes for pixel/cat
idx3 = content.find("def _default_scenes")
if idx3 >= 0:
    end = content.find("def ", idx3+50)
    snippet = content[idx3:end] if end > idx3 else content[idx3:idx3+500]
    print("\n=== _default_scenes ===")
    print(snippet.encode("ascii", errors="replace").decode())

# Check _default_script for "pixel" or "cat"
idx4 = content.find("def _default_script")
if idx4 >= 0:
    end = content.find("def ", idx4+50)
    snippet = content[idx4:end] if end > idx4 else content[idx4:idx4+500]
    print("\n=== _default_script ===")
    print(snippet.encode("ascii", errors="replace").decode())

sftp.close()
client.close()
