# utils/rsa_handler.py
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64

PRIVATE_KEY = RSA.generate(2048)
PUBLIC_KEY = PRIVATE_KEY.publickey().export_key().decode()

def decrypt_password(encrypted):
    cipher = PKCS1_v1_5.new(PRIVATE_KEY)
    decrypted = cipher.decrypt(base64.b64decode(encrypted), None)
    print("解密后的值为",decrypted)
    return decrypted.decode()