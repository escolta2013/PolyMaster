
import asyncio
import json
import httpx
from app.core.client import PolyClient

async def test_tokens():
    poly = PolyClient.get_instance()
    async with httpx.AsyncClient() as client:
        # Search for a popular market
        resp = await client.get("https://gamma-api.polymarket.com/markets?q=Bitcoin&active=true")
        markets = resp.json()
        for m in markets:
            print(f"Market: {m['question']}")
            tids = m.get('clobTokenIds')
            if isinstance(tids, str): tids = json.loads(tids)
            print(f"  TIDs: {tids}")
            if tids:
                for tid in tids:
                    ob = await poly.get_orderbook(tid)
                    print(f"    TID {tid}: Status={'OK' if ob['bids'] or ob['asks'] else 'Empty/404'}, Bids={len(ob['bids'])}, Asks={len(ob['asks'])}")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(test_tokens())
