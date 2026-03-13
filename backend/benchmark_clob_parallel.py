import asyncio
import time
import os
import sys
from dotenv import load_dotenv

# Add backend to path and load env
backend_path = os.path.join(os.getcwd(), "backend")
if os.path.exists(backend_path):
    sys.path.append(backend_path)
    load_dotenv(os.path.join(backend_path, ".env"))
else:
    sys.path.append(os.getcwd())
    load_dotenv(".env")

from app.core.client import PolyClient

async def benchmark_parallel(token_ids):
    client = PolyClient.get_instance()
    print(f"Parallel Benchmarking {len(token_ids)} CLOB price fetches...")
    
    start_total = time.time()
    
    async def fetch(tid):
        try:
            return await client.get_orderbook(tid)
        except:
            return None

    tasks = [fetch(tid) for tid in token_ids]
    results = await asyncio.gather(*tasks)
    
    end_total = time.time()
    valid = [r for r in results if r is not None]
    print(f"\n--- Parallel Results ---")
    print(f"Total time for {len(token_ids)} calls: {end_total - start_total:.2f}s")
    print(f"Success rate: {len(valid)}/{len(token_ids)}")

if __name__ == "__main__":
    import httpx
    
    async def run():
        async with httpx.AsyncClient() as c:
            r = await c.get("https://gamma-api.polymarket.com/markets", params={"limit": 50, "active": "true", "closed":"false"})
            markets = r.json()
            tids = []
            for m in markets:
                prices_str = m.get("clobTokenIds", "[]")
                import json
                try:
                    p_list = json.loads(prices_str) if isinstance(prices_str, str) else prices_str
                    if p_list: tids.append(p_list[0])
                except: continue
        
        await benchmark_parallel(tids[:10])
        await benchmark_parallel(tids[:30])
        await benchmark_parallel(tids[:50])

    asyncio.run(run())
