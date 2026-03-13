
import os, sys, httpx, asyncio, json
from typing import Optional, List, Dict
from collections import defaultdict

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

def get_fine_category(q: str) -> str:
    ql = q.lower()
    if any(k in ql for k in ["temperature", "weather", "seoul", "degrees"]): return "WEATHER"
    if any(k in ql for k in ["nba", "basketball", "lebron", "curry"]): return "NBA"
    if any(k in ql for k in ["tennis", "atp", "wta", "open", "handicap"]): 
        if "tennis" in ql or any(x in ql for x in ["atp", "wta"]): return "TENNIS"
    if any(k in ql for k in ["bitcoin", "eth ", "ethereum", "crypto", "price of"]): return "CRYPTO"
    if any(k in ql for k in ["soccer", "football", "champions league", "premier league"]): return "SOCCER"
    return "OTROS"

async def run_category_audit():
    print("Iniciando auditoría detallada por sub-categorías...")
    s = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    all_rows = []
    offset = 0
    limit = 1000
    while True:
        res = s.table('autonomous_logs').select('*').eq('decision', 'WOULD_EXECUTE').range(offset, offset + limit - 1).execute()
        if not res.data: break
        all_rows.extend(res.data)
        if len(res.data) < limit: break
        offset += limit

    seen = {}
    for r in all_rows:
        mid = r["market_id"]
        if mid not in seen or r["detected_at"] < seen[mid]["detected_at"]:
            seen[mid] = r
    
    unique_markets = list(seen.values())
    
    results = defaultdict(lambda: {"W": 0, "L": 0, "P": 0, "roi_sum": 0.0, "invested": 0.0})

    async with httpx.AsyncClient() as client:
        batch_size = 30
        for i in range(0, len(unique_markets), batch_size):
            batch = unique_markets[i:i + batch_size]
            tasks = [fetch_final_price(client, m["market_id"]) for m in batch]
            prices = await asyncio.gather(*tasks)
            
            for m, final in zip(batch, prices):
                entry = float(m.get("best_ask") or 0.5)
                cat = get_fine_category(m["market_question"])
                
                if final is None:
                    results[cat]["P"] += 1
                else:
                    f = float(final)
                    results[cat]["invested"] += 10.0
                    if f >= 0.97: 
                        pnl = (10.0 / entry) - 10.0
                        results[cat]["W"] += 1
                        results[cat]["roi_sum"] += pnl
                    elif f <= 0.03:
                        results[cat]["L"] += 1
                        results[cat]["roi_sum"] -= 10.0
                    else:
                        results[cat]["P"] += 1
            
            print(f"Auditando {min(i + batch_size, len(unique_markets))}/{len(unique_markets)}...")

    print("\n" + "="*80)
    print(f"{'RANKING DE RENTABILIDAD POR CATEGORÍA (MANTENIDAS)':^80}")
    print("="*80)
    print(f"{'CATEGORÍA':<20} | {'W-L':<10} | {'ACC%':<10} | {'ROI TOTAL':<15} | {'P&L ($)':<12}")
    print("-" * 80)
    
    sorted_cats = sorted(results.items(), key=lambda x: x[1]["roi_sum"], reverse=True)
    
    for cat, s in sorted_cats:
        total_res = s["W"] + s["L"]
        if total_res == 0: continue
        acc = (s["W"] / total_res * 100)
        roi_pct = (s["roi_sum"] / s["invested"] * 100) if s["invested"] > 0 else 0
        print(f"{cat:<20} | {s['W']:>2}-{s['L']:<2} | {acc:>5.1f}% | {roi_pct:>+8.2f}% | {s['roi_sum']:>+8.2f} USD")

    print("="*80)

if __name__ == "__main__":
    asyncio.run(run_category_audit())
