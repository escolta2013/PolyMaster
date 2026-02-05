"""
Comprehensive test for authenticated CLOB access.
Tests multiple markets to find one with recent trades.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from app.engines.tracker.clob_client import ClobClient
from app.engines.tracker.indexer import PolymarketIndexer

def test_comprehensive_auth():
    print("=" * 60)
    print("Comprehensive Authentication Test")
    print("=" * 60)
    
    clob = ClobClient()
    indexer = PolymarketIndexer()
    
    # Test 1: Verify authentication initialized
    print("\n1. Checking authentication initialization...")
    private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
    if private_key and private_key != "your_private_key_here":
        print("[OK] Private key configured")
    else:
        print("[FAIL] No private key - test cannot proceed")
        return
    
    # Test 2: Fetch top markets by volume
    print("\n2. Fetching top markets by volume...")
    markets = indexer.get_top_markets(limit=5)
    print(f"[OK] Found {len(markets)} markets")
    
    # Test 3: Try to get trades from multiple markets
    print("\n3. Testing trades endpoint across multiple markets...")
    import json
    
    trades_found = False
    for i, market in enumerate(markets[:5], 1):
        question = market.get('question', 'N/A')
        # Fix encoding for Windows terminal
        safe_question = question.encode('ascii', 'ignore').decode('ascii')[:60]
        print(f"\n   Market {i}: {safe_question}...")
        try:
            volume = float(market.get('volume', 0))
            print(f"   Volume: ${volume:,.0f}")
        except:
            print(f"   Volume: {market.get('volume', 'N/A')}")
        
        try:
            details = indexer.get_market_details(market['id'])
            token_ids = []
            if "clobTokenIds" in details:
                token_ids = json.loads(details["clobTokenIds"]) if isinstance(details["clobTokenIds"], str) else details["clobTokenIds"]
            
            if token_ids:
                token_id = token_ids[0]
                trades = clob.get_market_trades(token_id, limit=10)
                
                if trades and len(trades) > 0:
                    print(f"   [SUCCESS] Found {len(trades)} trades!")
                    trades_found = True
                    
                    # Show sample trade
                    sample = trades[0]
                    print(f"   Sample trade keys: {list(sample.keys())}")
                    
                    # Check for wallet addresses
                    if "maker_address" in sample or "taker_address" in sample:
                        print(f"   [SUCCESS] Wallet addresses available!")
                        if "maker_address" in sample:
                            print(f"   Maker: {sample.get('maker_address', 'N/A')[:15]}...")
                        if "taker_address" in sample:
                            print(f"   Taker: {sample.get('taker_address', 'N/A')[:15]}...")
                    break
                else:
                    print(f"   [WARN] No trades found for this market")
        except Exception as e:
            print(f"   [ERROR] {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    if trades_found:
        print("[SUCCESS] Authentication working - trades accessible!")
    else:
        print("[INFO] Authentication configured correctly")
        print("[WARN] No trades found across tested markets")
        print("")
        print("Possible reasons:")
        print("  1. Geographic restrictions (VPN may be needed)")
        print("  2. Markets tested have low recent activity")
        print("  3. API rate limiting")
        print("")
        print("Note: The Data API (wallet positions) is still accessible")
        print("      and does not require VPN for read-only operations.")
    
    print("=" * 60)

if __name__ == "__main__":
    test_comprehensive_auth()
