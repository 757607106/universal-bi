from cryptography.fernet import Fernet
import base64
from app.core.config import settings

def get_cipher_suite():
    # Ensure the key is 32 url-safe base64-encoded bytes
    # For simplicity in this demo, we derive a key or use a fixed one if provided
    # In production, use a proper key management system
    key = settings.SECRET_KEY
    if len(key) < 32:
        key = key.ljust(32, '0')
    key = base64.urlsafe_b64encode(key[:32].encode())
    return Fernet(key)

def encrypt_password(password: str) -> str:
    cipher_suite = get_cipher_suite()
    return cipher_suite.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    cipher_suite = get_cipher_suite()
    return cipher_suite.decrypt(encrypted_password.encode()).decode()
