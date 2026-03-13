import httpx
import json
import asyncio
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

async def inspect():
    client = PolyClient.get_instance()
    r = httpx.get("https://gamma-api.polymarket.com/markets", params={"limit": 15, "active": "true", "closed": "false"})
    data = r.json()
    print(f"{'Question':<40} | {'Gamma':<15} | {'CLOB':<15}")
    print("-" * 80)
    for m in data:
        tids_raw = m.get("clobTokenIds", "[]")
        tids = json.loads(tids_raw) if isinstance(tids_raw, str) else tids_raw
        if not tids: continue
        
        try:
            ob = await client.get_orderbook(tids[0])
            clob_price = ob.get("midpoint", "N/A")
            best_ask = ob.get("best_ask", "N/A")
            gamma_price = m.get("outcomePrices", ["N/A"])[0]
            print(f"{m['question'][:40]:<40} | {str(gamma_price):<15} | {str(clob_price)} (ask: {best_ask})")
        except:
            print(f"{m['question'][:40]:<40} | Error")

if __name__ == "__main__":
    asyncio.run(inspect())
