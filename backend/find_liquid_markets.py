
import asyncio
import json
from app.core.client import PolyClient
from app.core.config import settings

async def find_liquid_markets():
    poly = PolyClient.get_instance()
    # Fetch top markets via Gamma (which indexer uses)
    import httpx
    async with httpx.AsyncClient() as client:
        params = {
            "limit": 100,
            "order": "volume",
            "ascending": "false",
            "active": "true",
            "closed": "false"
        }
        resp = await client.get(f"{settings.GAMMA_API_URL}/markets", params=params)
        markets = resp.json()
        
        print(f"Fetched {len(markets)} markets from Gamma.")
        
        found = 0
        for m in markets:
            tids_raw = m.get("clobTokenIds", "[]")
            tids = json.loads(tids_raw) if isinstance(tids_raw, str) else tids_raw
            if not tids: continue
            
            # Check first token
            tid = tids[0]
            ob = await poly.get_orderbook(tid)
            
            p = ob.get("midpoint", 0.5)
            s = ob.get("spread", 1.0)
            d = ob.get("ask_depth", 0)
            
            if s < 0.25 and d > 10:
                print(f"MATCH: {m['question'][:50]}...")
                print(f"  P: {p:.3f} | S: {s:.3f} | D: {d:.1f}")
                found += 1
            elif found < 5:
                # Still print some rejects to see what's happening
                print(f"REJECT: {m['question'][:30]}... | P:{p:.3f} | S:{s:.3f} | D:{d:.1f}")
            
            if found >= 10: break

if __name__ == "__main__":
    asyncio.run(find_liquid_markets())
