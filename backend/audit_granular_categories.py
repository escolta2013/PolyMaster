
import os, sys, httpx, asyncio, json
from typing import Optional, List, Dict
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()
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

def categorize_granular(q: str) -> str:
    ql = q.lower()
    if any(k in ql for k in ["temperature", "rain", "precipitation", "snow", "degrees", "highest temperature"]): return "CLIMA"
    if any(k in ql for k in ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "crypto", "doge", "pepe"]): return "CRIPTO"
    if any(k in ql for k in ["election", "president", "trump", "biden", "harris", "senate", "house", "republican", "democrat"]): return "POLÍTICA"
    if any(k in ql for k in ["dota 2", "counter-strike", "valorant", "lol:", "league of legends", "esports"]): return "ESPORTS"
    if any(k in ql for k in ["nba", "basketball", "warriors", "lakers", "celtics", "points", "rebounds"]): return "NBA/BASQUET"
    if any(k in ql for k in ["ufc", "fight", "knockout", "mma"]): return "UFC/MMA"
    if any(k in ql for k in ["tennis", "atp", "wta", "nadal", "djokovic", "alcaraz"]): return "TENIS"
    if any(k in ql for k in ["chelsea", "arsenal", "liverpool", "real madrid", "barcelona", "bayern", "premier league", "champions league"]): return "FÚTBOL"
    if any(k in ql for k in ["win", "score", "player", "vs.", "team", "spread", "o/u"]): return "DEPORTES (VARIOS)"
    return "MISCELÁNEO"

async def run_granular_audit():
    print("Iniciando auditoría...")
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    res = supabase.table("autonomous_logs").select("market_id, market_question, best_ask").eq("decision", "WOULD_EXECUTE").execute()
    rows = res.data or []
    seen = {}
    for r in rows:
        mid = r["market_id"]
        if mid not in seen and r.get("best_ask"): seen[mid] = r
    
    unique_markets = list(seen.values())
    print(f"Total: {len(unique_markets)}")
    results = defaultdict(lambda: {"WIN": 0, "LOSS": 0, "PEND": 0})
    
    async with httpx.AsyncClient() as client:
        batch_size = 30
        for i in range(0, len(unique_markets), batch_size):
            batch = unique_markets[i:i + batch_size]
            tasks = [fetch_final_price(client, m["market_id"]) for m in batch]
            prices = await asyncio.gather(*tasks)
            for m, final in zip(batch, prices):
                cat = categorize_granular(m["market_question"])
                if final is None: results[cat]["PEND"] += 1
                else:
                    f = float(final)
                    if f >= 0.97: results[cat]["WIN"] += 1
                    elif f <= 0.03: results[cat]["LOSS"] += 1
                    else: results[cat]["PEND"] += 1
    
    print("-" * 50)
    with open("backend/audit_results.json", "w") as f_out:
        json.dump(results, f_out)
    for cat in sorted(results.keys()):
        s = results[cat]
        tot = s["WIN"] + s["LOSS"]
        acc = (s["WIN"]/tot*100) if tot > 0 else 0
        print(f"CAT: {cat:20} | W:{s['WIN']:3} | L:{s['LOSS']:3} | P:{s['PEND']:3} | ACC:{acc:5.1f}%")
    print("-" * 50)

if __name__ == "__main__":
    asyncio.run(run_granular_audit())
