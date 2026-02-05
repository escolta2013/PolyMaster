"""
Test script for Data API integration.
Verifies that we can:
1. Fetch orderbook using py-clob-client SDK
2. Fetch wallet positions using Data API
3. Analyze position data
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.engines.tracker.clob_client import ClobClient
from app.engines.tracker.indexer import PolymarketIndexer

def test_data_api_integration():
    print("=" * 60)
    print("Testing Data API Integration")
    print("=" * 60)
    
    # Initialize clients
    clob = ClobClient()
    indexer = PolymarketIndexer()
    
    # 1. Test: Fetch active markets
    print("\n1. Fetching top markets...")
    markets = indexer.get_top_markets(limit=3)
    if markets:
        print(f"[OK] Found {len(markets)} markets")
        market = markets[0]
        print(f"   Top market: {market.get('question', 'N/A')}")
        print(f"   Volume: ${float(market.get('volume', 0)):,.0f}")
    else:
        print("[FAIL] No markets found")
        return
    
    # 2. Test: Fetch orderbook using SDK
    print("\n2. Testing orderbook fetch with SDK...")
    try:
        import json
        details = indexer.get_market_details(market['id'])
        token_ids = []
        if "clobTokenIds" in details:
            token_ids = json.loads(details["clobTokenIds"]) if isinstance(details["clobTokenIds"], str) else details["clobTokenIds"]
        
        if token_ids:
            token_id = token_ids[0]
            print(f"   Token ID: {token_id[:20]}...")
            
            book = clob.get_orderbook(token_id)
            bids = book.get("bids", [])
            asks = book.get("asks", [])
            
            print(f"[OK] Orderbook fetched: {len(bids)} bids, {len(asks)} asks")
            if bids:
                print(f"   Best bid: ${bids[0]['price']} (size: {bids[0]['size']})")
        else:
            print("[WARN] No token IDs found")
    except Exception as e:
        print(f"[FAIL] Orderbook test failed: {e}")
    
    # 3. Test: Data API - User Positions
    print("\n3. Testing Data API (User Positions)...")
    # Using a test address (this will likely return empty, but tests the API)
    test_address = "0x0000000000000000000000000000000000000000"
    
    try:
        positions = clob.get_user_positions(test_address)
        print(f"[OK] Data API accessible: {len(positions)} positions found")
        
        if positions:
            print(f"   Sample position: {positions[0].keys()}")
    except Exception as e:
        print(f"[FAIL] Data API test failed: {e}")
    
    # 4. Test: Wallet Discovery (with empty seed)
    print("\n4. Testing wallet discovery...")
    try:
        discovered = indexer.discover_active_wallets(seed_addresses=[])
        print(f"[OK] Discovery method works: {len(discovered)} wallets found")
    except Exception as e:
        print(f"[FAIL] Discovery test failed: {e}")
    
    print("\n" + "=" * 60)
    print("Integration Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    test_data_api_integration()
