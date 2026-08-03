import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)
sftp = client.open_sftp()

with sftp.open("/opt/ubt-farm/bot/handlers.py", "rb") as f:
    content = f.read().decode("utf-8")

idx = content.find("async def _step1_generate_text")
if idx >= 0:
    snippet = content[idx:idx+1500]
    print(snippet.encode("ascii", errors="replace").decode())
else:
    print("_step1_generate_text NOT FOUND")

print("\n\n=== Checking if _run_build exists ===")
idx2 = content.find("def _run_build")
if idx2 >= 0:
    print("_run_build EXISTS in handlers.py!")
    print(content[idx2:idx2+200].encode("ascii", errors="replace").decode())
else:
    print("_run_build NOT in handlers.py")

# Also check what logging messages are used in builder.py
with sftp.open("/opt/ubt-farm/video_engine/builder.py", "rb") as f:
    bld = f.read().decode("utf-8")

print("\n\n=== Builder _log calls ===")
for line in bld.split("\n"):
    if "_log(" in line:
        clean = line.strip().encode("ascii", errors="replace").decode()
        print(clean)

sftp.close()
client.close()
