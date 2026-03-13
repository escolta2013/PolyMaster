
import asyncio
import httpx
from app.core.config import settings
from app.core.client import PolyClient
import json

async def debug_spreads():
    client = PolyClient.get_instance()
    async with httpx.AsyncClient() as h_client:
        # Fetch top 20 markets by volume
        params = {
            "limit": 20,
            "order": "volume",
            "ascending": "false",
            "active": "true",
            "closed": "false"
        }
        resp = await h_client.get(f"{settings.GAMMA_API_URL}/markets", params=params)
        markets = resp.json()
        
        print(f"{'Question':<50} | {'Price':<6} | {'Spread':<6} | {'Vol':<10}")
        print("-" * 80)
        
        for m in markets:
            tids_raw = m.get("clobTokenIds") or "[]"
            tids = json.loads(tids_raw) if isinstance(tids_raw, str) else tids_raw
            
            if not tids:
                print(f"{m.get('question')[:50]:<50} | NO TIDS")
                continue
                
            try:
                ob = await client.get_orderbook(tids[0])
                p = ob.get("midpoint", 0)
                s = ob.get("spread", 0)
                v = m.get("volume", 0)
                print(f"{m.get('question')[:50]:<50} | {p:<6.3f} | {s:<6.3f} | {v:<10}")
            except Exception as e:
                print(f"{m.get('question')[:50]:<50} | ERROR: {str(e)[:20]}")

if __name__ == "__main__":
    asyncio.run(debug_spreads())
