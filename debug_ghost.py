import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.engines.ghost.scanner import MarketScanner

async def test_scanner():
    scanner = MarketScanner()
    print("Scanning...")
    resp = scanner.client.get_sampling_simplified_markets(next_cursor="")
    raw_markets = resp.get('data') if isinstance(resp, dict) else resp
    print(f"Raw markets type: {type(raw_markets)}")
    if raw_markets:
        print(f"First item type: {type(raw_markets[0])}")
        print(f"First item keys: {dir(raw_markets[0]) if not isinstance(raw_markets[0], dict) else raw_markets[0].keys()}")
        print(f"First item: {raw_markets[0]}")
    
    results = scanner.scan_hype_spikes()
    print(f"Found {len(results)} results")

if __name__ == "__main__":
    asyncio.run(test_scanner())
