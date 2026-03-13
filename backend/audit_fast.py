
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
    esports_kw = ["dota 2", "counter-strike", "valorant", "lol:", "league of legends"]
    if any(k in ql for k in esports_kw): return "EXCLUIDA_ESPORTS"
    if ("win on 2026-" in ql and "both teams" not in ql and "o/u" not in ql): return "EXCLUIDA_FUTBOL"
    if any(k in ql for k in ["close above $", "nvidia", "bitcoin be between"]): return "EXCLUIDA_PRECIO"
    return "MANTENIDA"

async def run_audit():
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    res = supabase.table("autonomous_logs").select("*").eq("decision", "WOULD_EXECUTE").execute()
    
    rows = res.data or []
    seen = {}
    for r in rows:
        mid = r["market_id"]
        if mid not in seen and r.get("best_ask"): seen[mid] = r
    
    unique_markets = list(seen.values())
    
    results = {
        "MANTENIDA": {"WIN": 0, "LOSS": 0, "PENDING": 0},
        "EXCLUIDA_ESPORTS": {"WIN": 0, "LOSS": 0, "PENDING": 0},
        "EXCLUIDA_FUTBOL": {"WIN": 0, "LOSS": 0, "PENDING": 0},
        "EXCLUIDA_PRECIO": {"WIN": 0, "LOSS": 0, "PENDING": 0},
    }

    async with httpx.AsyncClient() as client:
        tasks = [fetch_final_price(client, m["market_id"]) for m in unique_markets]
        prices = await asyncio.gather(*tasks)
        
    for m, final in zip(unique_markets, prices):
        cat = categorize(m["market_question"])
        if final is None:
            results[cat]["PENDING"] += 1
        else:
            f = float(final)
            if f >= 0.97: results[cat]["WIN"] += 1
            elif f <= 0.03: results[cat]["LOSS"] += 1
            else: results[cat]["PENDING"] += 1

    with open("audit_final_report.json", "w") as f:
        json.dump(results, f, indent=4)
    
    print("DONE. Report saved to audit_final_report.json")

if __name__ == "__main__":
    asyncio.run(run_audit())
