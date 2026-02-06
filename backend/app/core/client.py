import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("PolyMasterClient")

class PolyClient:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls._create_client()
        return cls._instance

    @staticmethod
    def _create_client():
        host = "https://clob.polymarket.com"
        key = os.getenv("POLYMARKET_PRIVATE_KEY")
        chain_id = int(os.getenv("POLYMARKET_CHAIN_ID", "137"))
        
        # Explicit API Creds if user provided them
        api_key = os.getenv("POLYMARKET_API_KEY")
        api_secret = os.getenv("POLYMARKET_SECRET")
        api_passphrase = os.getenv("POLYMARKET_PASSPHRASE")

        if not key:
            print("(!) No Private Key found. Initializing Read-Only Client.")
            return ClobClient(host, chain_id=chain_id)

        print(f"Initializing PolyClient with Chain ID: {chain_id}...")

        try:
            # 1. Try fully authenticated initialization
            if api_key and api_secret and api_passphrase:
                print(" [x] Found API Keys in .env, using them directly.")
                creds = ApiCreds(api_key, api_secret, api_passphrase)
                return ClobClient(host, key=key, chain_id=chain_id, signature_type=1, creds=creds)
            
            # 2. If no API keys, try to derive them
            print(" [!] No API Keys found in .env. Attempting to DERIVE from Private Key...")
            temp_client = ClobClient(host, key=key, chain_id=chain_id, signature_type=1)
            try:
                creds = temp_client.create_or_derive_api_creds()
                print(f" [x] Credentials Derived! Key: {creds.api_key[:10]}...")
                return ClobClient(host, key=key, chain_id=chain_id, signature_type=1, creds=creds)
            except Exception as e:
                print(f" [!] Derivation failed: {e}")
                print("Fallback to L1-only client (Trading might fail).")
                return temp_client

        except Exception as e:
            print(f"Error initializing client: {e}")
            raise e
