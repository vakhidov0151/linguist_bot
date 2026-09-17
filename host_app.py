import subprocess
import re
import os
import time

def main():
    print("Web serverni ishga tushiramiz...")
    http_proc = subprocess.Popen(["python", "-m", "http.server", "8080", "--directory", "webapp"])
    
    print("Internetga ulayapmiz (Cloudflare)...")
    cf_proc = subprocess.Popen(
        ["cloudflared.exe", "tunnel", "--url", "http://localhost:8080"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    url = None
    for line in cf_proc.stdout:
        print("CF:", line.strip())
        match = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
        if match:
            url = match.group(1)
            break
            
    if not url:
        print("Xatolik: URL topilmadi.")
        return

    print(f"\n[+] YANGI MANZIL TOPILDI: {url}")
    
    with open(".env", "r") as f:
        env_content = f.read()
    
    env_content = re.sub(r'WEBAPP_URL=.*', f'WEBAPP_URL={url}', env_content)
    
    with open(".env", "w") as f:
        f.write(env_content)
        
    print("[+] .env fayli yangilandi!")
    
    print("Tunnel ochiq! Uni yopish uchun Ctrl+C bosing...")
    try:
        cf_proc.wait()
    except KeyboardInterrupt:
        http_proc.kill()
        cf_proc.kill()

if __name__ == "__main__":
    main()
