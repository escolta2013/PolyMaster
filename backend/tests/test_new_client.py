"""
Test creating a new client with derived credentials.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from py_clob_client.client import ClobClient

def test_new_client_with_creds():
    print("=" * 60)
    print("Testing New Client with Derived Credentials")
    print("=" * 60)
    
    private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
    
    # Step 1: Create temporary client to derive credentials
    print("\n1. Creating temporary client to derive credentials...")
    temp_client = ClobClient(
        host="https://clob.polymarket.com",
        key=private_key,
        chain_id=137,
        signature_type=1
    )
    
    print("\n2. Deriving credentials...")
    creds = temp_client.create_or_derive_api_creds()
    print(f"[OK] Derived credentials")
    print(f"     API Key: {creds.api_key[:20]}...")
    
    # Step 2: Create NEW client with both private key AND derived credentials
    print("\n3. Creating new authenticated client with derived creds...")
    try:
        auth_client = ClobClient(
            host="https://clob.polymarket.com",
            key=private_key,
            chain_id=137,
            signature_type=1,
            creds=creds  # Pass credentials during initialization
        )
        print("[OK] Authenticated client created")
    except Exception as e:
        print(f"[FAIL] Client creation failed: {e}")
        return
    
    # Step 3: Test trades endpoint
    print("\n4. Testing trades endpoint with authenticated client...")
    try:
        token_id = "36280081303832733684044815792389808710303922909687936060797841558107825922458"
        trades = auth_client.get_trades(token_id)
        print(f"[SUCCESS] Trades accessible!")
        if trades:
            trade_list = list(trades)
            print(f"          Found {len(trade_list)} trades")
            if trade_list:
                print(f"          Sample trade: {trade_list[0]}")
    except Exception as e:
        print(f"[FAIL] {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_new_client_with_creds()
