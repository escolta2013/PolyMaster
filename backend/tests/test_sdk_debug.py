"""
Debug script to test SDK credential derivation.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from py_clob_client.client import ClobClient

def test_credential_derivation():
    print("=" * 60)
    print("Testing SDK Credential Derivation")
    print("=" * 60)
    
    private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
    
    if not private_key or private_key == "your_private_key_here":
        print("[FAIL] No private key found in .env")
        return
    
    print(f"\n[OK] Private key detected: {private_key[:10]}...")
    
    # Initialize client with private key
    print("\nInitializing SDK client...")
    try:
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=private_key,
            chain_id=137,
            signature_type=1
        )
        print("[OK] Client initialized")
    except Exception as e:
        print(f"[FAIL] Client initialization failed: {e}")
        return
    
    # Try to derive API credentials
    print("\nDeriving API credentials...")
    try:
        creds = client.create_or_derive_api_creds()
        print(f"[OK] Credentials derived!")
        print(f"     Type: {type(creds)}")
        if isinstance(creds, dict):
            print(f"     Keys: {list(creds.keys())}")
        else:
            print(f"     Value: {creds}")
    except Exception as e:
        print(f"[FAIL] Credential derivation failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Try to fetch trades
    print("\nTesting trades endpoint...")
    try:
        # Use a popular market token ID
        token_id = "36280081303832733684044815792389808710303922909687936060797841558107825922458"
        trades = client.get_trades(token_id)
        print(f"[SUCCESS] Fetched trades: {type(trades)}")
        if trades:
            print(f"          Count: {len(list(trades)) if hasattr(trades, '__iter__') else 'N/A'}")
    except Exception as e:
        print(f"[FAIL] Trades fetch failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_credential_derivation()
