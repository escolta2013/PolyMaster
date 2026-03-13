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

async def benchmark_clob(token_ids):
    client = PolyClient.get_instance()
    print(f"Benchmarking {len(token_ids)} CLOB price fetches...")
    
    start_total = time.time()
    latencies = []
    
    for tid in token_ids:
        start = time.time()
        try:
            # We use get_orderbook which is what the Director uses
            res = await client.get_orderbook(tid)
            latencies.append(time.time() - start)
        except Exception as e:
            print(f"Error fetching {tid}: {e}")
    
    end_total = time.time()
    avg = sum(latencies) / len(latencies) if latencies else 0
    print(f"\n--- Results ---")
    print(f"Total time: {end_total - start_total:.2f}s")
    print(f"Average latency per call: {avg*1000:.2f}ms")
    print(f"Max latency: {max(latencies)*1000:.2f}ms" if latencies else "")
    print(f"Min latency: {min(latencies)*1000:.2f}ms" if latencies else "")

if __name__ == "__main__":
    # Sample token IDs from the previous log or just common ones
    # Will the Oklahoma City Thunder win the 2026 NBA Finals? (YES) - 21695420138947883296068249080063529341492336214570530739958787724213038661664
    # (Replacing with a few known IDs if I can find them, or I'll just pull them from a fresh Gamma fetch)
    import httpx
    
    async def run():
        async with httpx.AsyncClient() as c:
            r = await c.get("https://gamma-api.polymarket.com/markets", params={"limit": 10, "active": "true", "closed":"false"})
            markets = r.json()
            tids = []
            for m in markets:
                prices_str = m.get("clobTokenIds", "[]")
                import json
                try:
                    p_list = json.loads(prices_str) if isinstance(prices_str, str) else prices_str
                    if p_list: tids.append(p_list[0])
                except: continue
        
        await benchmark_clob(tids)

    asyncio.run(run())
