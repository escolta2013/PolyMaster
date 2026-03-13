"""
Test if credentials persist after create_or_derive_api_creds.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from py_clob_client.client import ClobClient

def test_credential_persistence():
    print("=" * 60)
    print("Testing Credential Persistence")
    print("=" * 60)
    
    private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
    
    # Initialize client
    print("\n1. Initializing client...")
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=private_key,
        chain_id=137,
        signature_type=1
    )
    print("[OK] Client initialized")
    
    # Check if client has creds attribute before derivation
    print("\n2. Checking client.creds before derivation...")
    print(f"   Has 'creds' attr: {hasattr(client, 'creds')}")
    if hasattr(client, 'creds'):
        print(f"   creds value: {client.creds}")
    
    # Derive credentials
    print("\n3. Deriving credentials...")
    derived_creds = client.create_or_derive_api_creds()
    print(f"[OK] Derived: {derived_creds}")
    
    # Check if client has creds attribute after derivation
    print("\n4. Checking client.creds after derivation...")
    print(f"   Has 'creds' attr: {hasattr(client, 'creds')}")
    if hasattr(client, 'creds'):
        print(f"   creds value: {client.creds}")
        print(f"   creds == derived_creds: {client.creds == derived_creds}")
    
    # Try to access trades
    print("\n5. Testing trades access...")
    try:
        token_id = "36280081303832733684044815792389808710303922909687936060797841558107825922458"
        trades = client.get_trades(token_id)
        print(f"[SUCCESS] Trades accessible!")
    except Exception as e:
        print(f"[FAIL] {e}")
        
        # Try manually setting creds
        print("\n6. Trying manual credential assignment...")
        client.creds = derived_creds
        print(f"   Manually set client.creds = {client.creds}")
        
        try:
            trades = client.get_trades(token_id)
            print(f"[SUCCESS] Trades accessible after manual assignment!")
        except Exception as e2:
            print(f"[FAIL] Still failing: {e2}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_credential_persistence()
