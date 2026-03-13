"""
Test get_trades with correct parameter format.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import TradeParams

def test_trades_with_params():
    print("=" * 60)
    print("Testing get_trades with TradeParams")
    print("=" * 60)
    
    private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
    
    # Derive credentials
    print("\n1. Deriving credentials...")
    temp_client = ClobClient(
        host="https://clob.polymarket.com",
        key=private_key,
        chain_id=137,
        signature_type=1
    )
    creds = temp_client.create_or_derive_api_creds()
    print(f"[OK] Credentials derived")
    
    # Create authenticated client
    print("\n2. Creating authenticated client...")
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=private_key,
        chain_id=137,
        signature_type=1,
        creds=creds
    )
    print("[OK] Client ready")
    
    # Test with TradeParams object
    print("\n3. Fetching trades with TradeParams...")
    try:
        token_id = "36280081303832733684044815792389808710303922909687936060797841558107825922458"
        
        # Create TradeParams object
        params = TradeParams(market=token_id)
        trades = client.get_trades(params)
        
        print(f"[SUCCESS] Trades fetched!")
        trade_list = list(trades)
        print(f"          Count: {len(trade_list)}")
        
        if trade_list:
            print(f"\n          Sample trade:")
            sample = trade_list[0]
            if hasattr(sample, '__dict__'):
                for key, value in vars(sample).items():
                    print(f"            {key}: {value}")
            else:
                print(f"            {sample}")
    except Exception as e:
        print(f"[FAIL] {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_trades_with_params()
