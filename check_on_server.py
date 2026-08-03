import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("144.31.25.159", 22, "root", "BYAgu5iR5RgE0XuA", timeout=15)
sftp = client.open_sftp()

# Check handlers.py for _step1_generate_text
with sftp.open("/opt/ubt-farm/bot/handlers.py", "rb") as f:
    content = f.read().decode("utf-8")

has_step1 = "_step1_generate_text" in content
has_pixel = "pixel" in content.lower()
has_cat = "черный пиксельный котик" in content
has_breakdown = "СЦЕНАРИЙ" in content
print(f"Has _step1_generate_text: {has_step1}")
print(f"Has pixel/cat references: {has_pixel}/{has_cat}")
print(f"Has СЦЕНАРИЙ breakdown: {has_breakdown}")

# Check llm_client.py for key fix
with sftp.open("/opt/ubt-farm/core/llm_client.py", "rb") as f:
    llm = f.read().decode("utf-8")

has_vpn_key = '"vpn и приватность"' in llm
has_pixel_prompts = "pixel" in llm.lower()
has_black_cat = "black pixel cat" in llm
print(f"Has 'vpn и приватность' key: {has_vpn_key}")
print(f"Has pixel prompts: {has_pixel_prompts}")
print(f"Has black pixel cat in prompts: {has_black_cat}")

# Check image_gen.py 
with sftp.open("/opt/ubt-farm/core/image_gen.py", "rb") as f:
    img = f.read().decode("utf-8")

has_pixel_fallback = "pixel_size" in img or "px" in img[:200] or "pixel" in img.lower()
print(f"Has pixel fallback generator: {has_pixel_fallback}")

sftp.close()
client.close()
