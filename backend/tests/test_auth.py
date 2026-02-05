"""
Test authenticated CLOB access with user's Builder API credentials.
This will verify that we can now access the /trades endpoint.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from app.engines.tracker.clob_client import ClobClient
from app.engines.tracker.indexer import PolymarketIndexer

def test_authenticated_access():
    print("=" * 60)
    print("Testing Authenticated CLOB Access")
    print("=" * 60)
    
    # Initialize client (will auto-detect credentials from .env)
    clob = ClobClient()
    indexer = PolymarketIndexer()
    
    # 1. Verify authentication status
    print("\n1. Checking authentication status...")
    private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
    if private_key and private_key != "your_private_key_here":
        print("[OK] Credentials detected in .env")
    else:
        print("[WARN] No credentials found - running in read-only mode")
        print("      Please update .env with your Polymarket credentials")
        return
    
    # 2. Test: Fetch markets
    print("\n2. Fetching active markets...")
    markets = indexer.get_top_markets(limit=2)
    if not markets:
        print("[FAIL] Could not fetch markets")
        return
    
    market = markets[0]
    print(f"[OK] Testing with market: {market.get('question', 'N/A')[:50]}...")
    
    # 3. Test: Get token IDs
    print("\n3. Getting token IDs...")
    import json
    details = indexer.get_market_details(market['id'])
    token_ids = []
    if "clobTokenIds" in details:
        token_ids = json.loads(details["clobTokenIds"]) if isinstance(details["clobTokenIds"], str) else details["clobTokenIds"]
    
    if not token_ids:
        print("[FAIL] No token IDs found")
        return
    
    token_id = token_ids[0]
    print(f"[OK] Token ID: {token_id[:20]}...")
    
    # 4. Test: Fetch trades (AUTHENTICATED ENDPOINT)
    print("\n4. Testing authenticated /trades endpoint...")
    try:
        trades = clob.get_market_trades(token_id)
        
        if trades and len(trades) > 0:
            print(f"[SUCCESS] Fetched {len(trades)} trades!")
            print(f"          Sample trade keys: {list(trades[0].keys())}")
            
            # Check for wallet addresses
            if "maker_address" in trades[0] or "taker_address" in trades[0]:
                print(f"[SUCCESS] Wallet addresses available in trade data!")
                if "maker_address" in trades[0]:
                    print(f"          Maker: {trades[0]['maker_address'][:10]}...")
                if "taker_address" in trades[0]:
                    print(f"          Taker: {trades[0]['taker_address'][:10]}...")
            else:
                print(f"[WARN] No wallet addresses in trade data")
        else:
            print("[WARN] Trades endpoint returned empty list")
            print("       This might mean no recent trades for this market")
    except Exception as e:
        print(f"[FAIL] Trades endpoint failed: {e}")
        print("       Check that your API credentials are correct")
    
    # 5. Test: Get market traders (should now work!)
    print("\n5. Testing get_market_traders with auth...")
    try:
        traders = indexer.get_market_traders(market['id'])
        print(f"[OK] Found {len(traders)} unique traders")
        if traders:
            print(f"    Sample addresses:")
            for addr in traders[:3]:
                print(f"      - {addr[:10]}...")
    except Exception as e:
        print(f"[FAIL] get_market_traders failed: {e}")
    
    print("\n" + "=" * 60)
    print("Authentication Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    test_authenticated_access()
