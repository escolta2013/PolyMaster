from cryptography.fernet import Fernet
from app.core.config import settings
from app.core.logging import logger
import base64
import os

class WalletVault:
    """
    Handles encryption and decryption of private keys using AES-256 (Fernet).
    """
    
    def __init__(self):
        key = settings.WALLET_ENCRYPTION_KEY
        if not key:
            logger.warning("WALLET_ENCRYPTION_KEY not set. Generating a temporary one for this session.")
            key = Fernet.generate_key().decode()
            
        # Ensure key is valid Fernet key (32 url-safe base64-encoded bytes)
        try:
            self.fernet = Fernet(key.encode())
        except Exception as e:
            logger.error(f"Invalid WALLET_ENCRYPTION_KEY: {e}")
            raise ValueError("Invalid WALLET_ENCRYPTION_KEY")

    def encrypt_key(self, private_key: str) -> str:
        """Encrypt a private key string."""
        if private_key.startswith("0x"):
            private_key = private_key[2:]
        encrypted = self.fernet.encrypt(private_key.encode())
        return encrypted.decode()

    def decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt an encrypted private key string."""
        decrypted = self.fernet.decrypt(encrypted_key.encode())
        return decrypted.decode()

vault = WalletVault()
