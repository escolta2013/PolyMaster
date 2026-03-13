
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
    return "OTHER"

async def run_sql_mock_report():
    print("Fetching WOULD_EXECUTE trades & Gamma API final prices to simulate your SQL Queries...")
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

    resolved_markets = []

    async with httpx.AsyncClient() as client:
        batch_size = 30
        for i in range(0, len(unique_markets), batch_size):
            batch = unique_markets[i:i + batch_size]
            tasks = [fetch_final_price(client, m["market_id"]) for m in batch]
            prices = await asyncio.gather(*tasks)
            
            for m, final in zip(batch, prices):
                if final is not None:
                    f = float(final)
                    # ONLY DEFINITELY RESOLVED (As per SQL: >0.97 OR <0.03)
                    if f >= 0.97 or f <= 0.03:
                        m["final_price"] = f
                        m["won"] = (f >= 0.97)
                        
                        # Edge net formula: score - current_price - (spread * 0.5)
                        score = m.get("council_score", 0)
                        ask = m.get("best_ask", 0.5)
                        spread = m.get("spread", 0.0)
                        m["edge_net"] = score - ask - (spread * 0.5)
                        
                        m["category"] = get_fine_category(m["market_question"])
                        
                        agent_scores = {}
                        if isinstance(m["reasoning"], str):
                            try:
                                agent_scores = json.loads(m["reasoning"])
                            except:
                                pass
                        elif isinstance(m["reasoning"], dict):
                            agent_scores = m["reasoning"]
                        m["agent_scores"] = agent_scores
                        
                        resolved_markets.append(m)

    # ---------------------------------------------------------
    # QUERY 1: SOURCE (We cannot do this since source isn't in DB, I will stub it)
    # ---------------------------------------------------------
    print("\n" + "="*80)
    print("CONSULTA 1 — Accuracy por fuente de señal (SOURCE NO ALMACENADO EN BD)")
    print("Nota: La columna 'source' no existe en 'autonomous_logs'. Se asume todo como UNKNOWN.")
    print("="*80)
    print(f"{'source':<20} | {'total':<6} | {'wins':<6} | {'accuracy':<8} | {'avg_c_score':<12} | {'avg_edge_net':<12}")
    print("-" * 80)
    total = len(resolved_markets)
    wins = sum(1 for m in resolved_markets if m["won"])
    acc = (wins / total * 100) if total > 0 else 0
    avg_score = sum(m["council_score"] for m in resolved_markets) / total if total > 0 else 0
    avg_edge = sum(m["edge_net"] for m in resolved_markets) / total if total > 0 else 0
    print(f"{'UNKNOWN':<20} | {total:<6} | {wins:<6} | {acc:>5.1f}%   | {avg_score:>12.3f} | {avg_edge:>12.3f}")

    # ---------------------------------------------------------
    # QUERY 2: EDGE BUCKETS
    # ---------------------------------------------------------
    buckets = {
        ">0.12": {"n": 0, "wins": 0},
        "0.07-0.12": {"n": 0, "wins": 0},
        "0.05-0.07": {"n": 0, "wins": 0},
        "<0.05": {"n": 0, "wins": 0}
    }
    for m in resolved_markets:
        en = m["edge_net"]
        if en >= 0.12: b = ">0.12"
        elif en >= 0.07: b = "0.07-0.12"
        elif en >= 0.05: b = "0.05-0.07"
        else: b = "<0.05"
        buckets[b]["n"] += 1
        if m["won"]: buckets[b]["wins"] += 1

    print("\n" + "="*80)
    print("CONSULTA 2 — Accuracy por bucket de Edge Neto")
    print("="*80)
    print(f"{'edge_bucket':<15} | {'n':<6} | {'wins':<6} | {'accuracy':<8}")
    print("-" * 80)
    for b in [">0.12", "0.07-0.12", "0.05-0.07", "<0.05"]:
        d = buckets[b]
        if d["n"] > 0:
             acc = (d["wins"]/d["n"]*100)
             print(f"{b:<15} | {d['n']:<6} | {d['wins']:<6} | {acc:>5.1f}%")

    # ---------------------------------------------------------
    # QUERY 3: CATEGORY
    # ---------------------------------------------------------
    cat_data = defaultdict(lambda: {"n": 0, "wins": 0, "ask_sum": 0.0})
    for m in resolved_markets:
        c = m["category"]
        cat_data[c]["n"] += 1
        if m["won"]: cat_data[c]["wins"] += 1
        cat_data[c]["ask_sum"] += m.get("best_ask", 0.5)

    print("\n" + "="*80)
    print("CONSULTA 3 — Accuracy por categoría (n >= 1)")
    print("="*80)
    print(f"{'category':<15} | {'n':<6} | {'wins':<6} | {'accuracy':<8} | {'avg_entry_price':<15}")
    print("-" * 80)
    sorted_cats = sorted(cat_data.items(), key=lambda x: (x[1]["wins"]/x[1]["n"] if x[1]["n"]>0 else 0), reverse=True)
    for c, d in sorted_cats:
        if d["n"] >= 1: # Lowered to 1 instead of 10 to see all data
             acc = (d["wins"]/d["n"]*100)
             avg_ask = d["ask_sum"] / d["n"]
             print(f"{c:<15} | {d['n']:<6} | {d['wins']:<6} | {acc:>5.1f}%   | {avg_ask:>10.3f}")

    # ---------------------------------------------------------
    # QUERY 4: AGENTS
    # ---------------------------------------------------------
    agents = {"FedWatcher": [], "RuleLawyer": [], "SentimentSwarm": [], "RiskArbiter": []}
    for m in resolved_markets:
        sc = m.get("agent_scores", {})
        for a in agents.keys():
            if a in sc:
                agents[a].append(sc[a])

    print("\n" + "="*80)
    print("CONSULTA 4 — Accuracy por agente individual del Council")
    print("="*80)
    overall_acc = (wins / total * 100) if total > 0 else 0
    print(f"Overall Accuracy:  {overall_acc:>5.1f}%")
    print(f"Total mercados (n): {total}")
    print("-" * 80)
    for a in agents.keys():
        if agents[a]:
            avg_a = sum(agents[a]) / len(agents[a])
            print(f"avg_{a.lower()}: {avg_a:.3f}")

    print("="*80)

if __name__ == "__main__":
    asyncio.run(run_sql_mock_report())
