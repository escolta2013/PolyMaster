
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from eth_account import Account

def debug():
    print("--- PolyMaster Wallet & Env Diagnostic ---")
    
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ ERROR: .env file not found!")
        return
    
    load_dotenv(env_path)
    
    # Check Wallet
    pk = os.getenv("PK")
    proxy = os.getenv("POLY_PROXY_ADDRESS")
    
    print("\n--- Wallet Identity ---")
    if not pk:
        print("❌ ERROR: PK (Private Key) missing in .env!")
    else:
        # Derive Public Address
        try:
            acc = Account.from_key(pk)
            derived_address = acc.address
            print(f"Derived Address (from PK): {derived_address}")
            print(f"Proxy Address (from .env): {proxy if proxy else 'NOT SET'}")
            
            # THE CRITICAL CHECK
            active_address = proxy if proxy else derived_address
            print(f"\n👉 THE BOT IS CHECKING THIS ADDRESS: {active_address}")
            print("   (Verify this address on PolygonScan to see if it matches where your money is)")
        except Exception as e:
            print(f"❌ ERROR deriving address: {e}")

    # Check RPCs again
    alchemy = os.getenv("ALCHEMY_RPC_URL")
    print(f"\n--- Connectivity ---")
    print(f"Alchemy present: {'✅' if alchemy else '❌'}")
    
if __name__ == "__main__":
    debug()
