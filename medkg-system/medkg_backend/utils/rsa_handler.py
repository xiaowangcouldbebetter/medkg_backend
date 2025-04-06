# utils/rsa_handler.py
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64

# 生成密钥对
PRIVATE_KEY = RSA.generate(2048)
PUBLIC_KEY = PRIVATE_KEY.publickey().export_key().decode()

def decrypt_password(encrypted):
    try:
        # 解密前的处理
        encrypted_bytes = base64.b64decode(encrypted)
        cipher = PKCS1_v1_5.new(PRIVATE_KEY)
        
        # 使用固定大小进行解密
        sentinel = None  # 使用默认sentinel值
        decrypted = cipher.decrypt(encrypted_bytes, sentinel)
        
        if decrypted:
            return decrypted.decode('utf-8')
        else:
            raise ValueError("解密失败")
    except Exception as e:
        print(f"解密过程中出错: {str(e)}")
        raise