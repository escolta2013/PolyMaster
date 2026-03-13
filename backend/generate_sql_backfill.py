
import os, sys, httpx, asyncio, json
from typing import Optional, List, Dict
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.abspath("."))

from app.core.config import settings
from supabase import create_client

async def fetch_market_status(client: httpx.AsyncClient, market_id: str) -> Dict:
    try:
        url = f"https://gamma-api.polymarket.com/markets/{market_id}"
        resp = await client.get(url, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            return {"id": market_id, "best_ask": data.get("bestAsk")}
    except: pass
    return {"id": market_id, "best_ask": None}

async def generate_sql_backfill():
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    res = supabase.table("autonomous_logs").select("id, market_id").eq("decision", "WOULD_EXECUTE").execute()
    rows = res.data or []
    
    wins = []
    losses = []
    
    async with httpx.AsyncClient() as client:
        batch_size = 50
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            tasks = [fetch_market_status(client, r["market_id"]) for r in batch]
            results = await asyncio.gather(*tasks)
            
            for row, status in zip(batch, results):
                ba = status.get("best_ask")
                if ba is not None:
                    if float(ba) >= 0.98: wins.append(str(row["id"]))
                    elif float(ba) <= 0.02: losses.append(str(row["id"]))
            
            print(f"Checking {min(i + batch_size, len(rows))}/{len(rows)}...")

    if wins:
        print(f"UPDATE public.autonomous_logs SET correct = 'WIN' WHERE id IN ({','.join(wins)});")
    if losses:
        print(f"UPDATE public.autonomous_logs SET correct = 'LOSS' WHERE id IN ({','.join(losses)});")

if __name__ == "__main__":
    asyncio.run(generate_sql_backfill())
