
import os, sys, httpx, asyncio
from typing import Optional, List, Dict
import json

# Fix paths
sys.path.insert(0, os.path.abspath("."))
from app.core.config import settings
from supabase import create_client

async def fetch_final_price(client: httpx.AsyncClient, market_id: str) -> Optional[float]:
    try:
        url = f"https://gamma-api.polymarket.com/markets/{market_id}"
        resp = await client.get(url, timeout=10.0)
        if resp.status_code == 200:
            return resp.json().get("bestAsk")
    except Exception:
        pass
    return None

def categorize(q: str) -> str:
    ql = q.lower()
    if any(k in ql for k in ["dota 2", "counter-strike", "valorant", "lol:", "esports"]): return "EXCLUIDA_ESPORTS"
    if ("win on 2026-" in ql and "both teams" not in ql and "o/u" not in ql): return "EXCLUIDA_FUTBOL"
    return "MANTENIDA"

async def run_audit():
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    # Fetch all WOULD_EXECUTE or EXECUTED
    res = supabase.table("autonomous_logs").select("*").in_("decision", ["WOULD_EXECUTE", "EXECUTED"]).execute()
    
    rows = res.data or []
    seen = {}
    for r in rows:
        mid = r["market_id"]
        # Use the EARLIEST entry as the entry price
        if mid not in seen: 
            seen[mid] = r
        else:
            if r["detected_at"] < seen[mid]["detected_at"]:
                seen[mid] = r
    
    unique_markets = list(seen.values())
    
    async with httpx.AsyncClient() as client:
        tasks = [fetch_final_price(client, m["market_id"]) for m in unique_markets]
        prices = await asyncio.gather(*tasks)
        
    stats = {
        "GLOBAL": {"W": 0, "L": 0, "P": 0, "total_pnl": 0.0},
        "MANTENIDA": {"W": 0, "L": 0, "P": 0, "total_pnl": 0.0},
    }

    for m, final in zip(unique_markets, prices):
        entry = float(m.get("best_ask") or 0.5) # Default to 0.5 if missing
        cat = categorize(m["market_question"])
        
        target = ["GLOBAL"]
        if cat == "MANTENIDA": target.append("MANTENIDA")
        
        if final is None:
            for t in target: stats[t]["P"] += 1
        else:
            f = float(final)
            if f >= 0.97: 
                # WIN: PnL = (1.0 - entry) / entry
                pnl = (1.0 - entry) / entry
                for t in target: 
                    stats[t]["W"] += 1
                    stats[t]["total_pnl"] += pnl
            elif f <= 0.03:
                # LOSS: PnL = -1.0
                pnl = -1.0
                for t in target:
                    stats[t]["L"] += 1
                    stats[t]["total_pnl"] += pnl
            else:
                for t in target: stats[t]["P"] += 1

    print(json.dumps(stats, indent=4))

if __name__ == "__main__":
    asyncio.run(run_audit())
