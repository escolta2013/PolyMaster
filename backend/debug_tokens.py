
import asyncio
import json
from app.core.client import PolyClient
from app.core.config import settings
import httpx

async def debug_tokens():
    poly = PolyClient.get_instance()
    async with httpx.AsyncClient() as client:
        # Fetch top markets via Gamma
        params = {"limit": 10, "order": "volume", "ascending": "false", "active": "true"}
        resp = await client.get(f"{settings.GAMMA_API_URL}/markets", params=params)
        markets = resp.json()
        
        for m in markets:
            print(f"\nMarket: {m['question']}")
            tids_raw = m.get("clobTokenIds") or "[]"
            tids = json.loads(tids_raw) if isinstance(tids_raw, str) else tids_raw
            print(f"  Gamma IDs: {tids}")
            
            for tid in tids:
                ob = await poly.get_orderbook(tid)
                print(f"    TID {tid}: Bids={len(ob['bids'])}, Asks={len(ob['asks'])}, Spread={ob['spread']}, Depth={ob['ask_depth']}")

if __name__ == "__main__":
    asyncio.run(debug_tokens())
