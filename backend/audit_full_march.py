
import os, sys, httpx, asyncio, json
from typing import Optional, List, Dict

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
    esports_kw = ["dota 2", "counter-strike", "valorant", "lol:", "esports", "map 1", "map 2"]
    if any(k in ql for k in esports_kw): return "EXCLUIDA_ESPORTS"
    if ("win on 2026-" in ql and "both teams" not in ql and "o/u" not in ql): return "EXCLUIDA_FUTBOL"
    if any(k in ql for k in ["close above $", "nvidia", "bitcoin be between", "nvda"]): return "EXCLUIDA_PRECIO"
    return "MANTENIDA"

async def run_full_audit():
    print("Iniciando auditoría completa de los 245 mercados WOULD_EXECUTE...")
    s = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    # Obtener TODOS los WOULD_EXECUTE con paginación
    all_rows = []
    offset = 0
    limit = 1000
    while True:
        res = s.table('autonomous_logs').select('*').eq('decision', 'WOULD_EXECUTE').range(offset, offset + limit - 1).execute()
        if not res.data: break
        all_rows.extend(res.data)
        if len(res.data) < limit: break
        offset += limit

    # Agrupar por mercado único (mantenemos el precio de entrada más antiguo)
    seen = {}
    for r in all_rows:
        mid = r["market_id"]
        if mid not in seen or r["detected_at"] < seen[mid]["detected_at"]:
            seen[mid] = r
    
    unique_markets = list(seen.values())
    print(f"Total mercados únicos a auditar: {len(unique_markets)}")
    
    stats = {
        "GLOBAL": {"W": 0, "L": 0, "P": 0, "roi_sum": 0.0},
        "MANTENIDA": {"W": 0, "L": 0, "P": 0, "roi_sum": 0.0},
        "EXCLUIDA": {"W": 0, "L": 0, "P": 0, "roi_sum": 0.0}
    }

    async with httpx.AsyncClient() as client:
        # Procesamos en lotes para no saturar la API
        batch_size = 20
        for i in range(0, len(unique_markets), batch_size):
            batch = unique_markets[i:i + batch_size]
            tasks = [fetch_final_price(client, m["market_id"]) for m in batch]
            prices = await asyncio.gather(*tasks)
            
            for m, final in zip(batch, prices):
                entry = float(m.get("best_ask") or 0.5)
                cat = categorize(m["market_question"])
                
                targets = ["GLOBAL"]
                if cat == "MANTENIDA": targets.append("MANTENIDA")
                else: targets.append("EXCLUIDA")
                
                if final is None:
                    for t in targets: stats[t]["P"] += 1
                else:
                    f = float(final)
                    if f >= 0.97: # WIN
                        pnl = (1.0 - entry) / entry
                        for t in targets:
                            stats[t]["W"] += 1
                            stats[t]["roi_sum"] += pnl
                    elif f <= 0.03: # LOSS
                        for t in targets:
                            stats[t]["L"] += 1
                            stats[t]["roi_sum"] -= 1.0 # -100%
                    else:
                        for t in targets: stats[t]["P"] += 1
            
            print(f"Procesados {min(i + batch_size, len(unique_markets))}/{len(unique_markets)}...")

    print("\n" + "="*50)
    for group, s in stats.items():
        total_res = s["W"] + s["L"]
        acc = (s["W"] / total_res * 100) if total_res > 0 else 0
        avg_roi = (s["roi_sum"] / total_res * 100) if total_res > 0 else 0
        print(f"GRUPO: {group}")
        print(f" - Accuracy: {acc:.1f}% ({s['W']}W - {s['L']}L)")
        print(f" - ROI Promedio: {avg_roi:+.2f}%")
        print(f" - Pendientes: {s['P']}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(run_full_audit())
