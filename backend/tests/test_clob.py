
import sys
import os
import asyncio

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.engines.tracker.clob_client import ClobClient
from app.engines.tracker.indexer import PolymarketIndexer

def test_clob_fetch():
    print("Testing ClobClient...")
    client = ClobClient()
    
    # Test 1: Get Sampling (Simplified view)
    # Using a known Token ID (e.g. from a top market, or just a random one if we can find it)
    # But better to use Indexer to find a top market first.
    
    indexer = PolymarketIndexer()
    print("Fetching top markets to get a valid Market ID...")
    markets = indexer.get_top_markets(limit=1)
    
    if not markets:
        print("FAIL: No markets found via Gamma API.")
        return

    top_market = markets[0]
    market_id = top_market.get("id")
    print(f"Top Market Data: {top_market}")
    
    if not market_id:
        print("FAIL: Market has no ID.")
        return

    print("Fetching active traders via CLOB integration...")
    traders = indexer.get_market_traders(market_id)
    
    print(f"Found {len(traders)} potential active traders.")
    if traders:
        print(f"Sample Traders: {traders[:5]}")
    else:
        print("WARNING: No traders found. This might be due to low activity or API mapping issues.")

    # Test direct CLOB Client usage if possible
    # We need a token_id.
    details = indexer.get_market_details(market_id)
    token_ids = []
    import json
    if "clobTokenIds" in details:
         token_ids = json.loads(details["clobTokenIds"]) if isinstance(details["clobTokenIds"], str) else details["clobTokenIds"]
    
    if token_ids:
        token_id = token_ids[0]
        print(f"Testing direct trades fetch for Token ID: {token_id}")
        trades = client.get_market_trades(token_id)
        if trades:
            print(f"Direct Trades found: {len(trades)}")
            print(f"First trade: {trades[0]}")
        else:
            print("No trades found (or empty list returned).")
            
        print(f"Testing Orderbook fetch for Token ID: {token_id}")
        orderbook = client.get_orderbook(token_id)
        if orderbook:
            bids = orderbook.get('bids', [])
            print(f"Orderbook found! Bids: {len(bids)}, Asks: {len(orderbook.get('asks', []))}")
            if bids:
                print(f"Sample Bid: {bids[0]}")
        else:
            print("Orderbook fetch failed.")
    
if __name__ == "__main__":
    test_clob_fetch()
