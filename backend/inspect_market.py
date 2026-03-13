
import asyncio
import json
from app.core.client import PolyClient
from app.core.config import settings
import httpx

async def inspect_top_market():
    async with httpx.AsyncClient() as client:
        # Get the top market by volume
        resp = await client.get(f"{settings.GAMMA_API_URL}/markets", params={"limit": 1, "order": "volume", "ascending": "false", "active": "true"})
        market = resp.json()[0]
        print(f"Market: {market['question']}")
        print(f"ID: {market['id']}")
        
        tids_raw = market.get("clobTokenIds", "[]")
        tids = json.loads(tids_raw) if isinstance(tids_raw, str) else tids_raw
        print(f"Token IDs: {tids}")
        
        poly = PolyClient.get_instance()
        for i, tid in enumerate(tids):
            print(f"\nChecking Orderbook for Token {i} ({tid}):")
            ob = await poly.get_orderbook(tid)
            print(f"  Best Bid: {ob['best_bid']}")
            print(f"  Best Ask: {ob['best_ask']}")
            print(f"  Spread: {ob['spread']}")
            print(f"  Bids count: {len(ob['bids'])}")
            print(f"  Asks count: {len(ob['asks'])}")
            if ob['bids']: print(f"  Top Bid: {ob['bids'][0]}")
            if ob['asks']: print(f"  Top Ask: {ob['asks'][0]}")

if __name__ == "__main__":
    asyncio.run(inspect_top_market())
