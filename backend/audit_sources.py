
import os, sys, glob, re, asyncio, httpx, json
from collections import defaultdict

sys.path.insert(0, os.path.abspath("."))
from app.core.config import settings
from supabase import create_client

async def fetch_final_price(client: httpx.AsyncClient, market_id: str) -> float | None:
    try:
        url = f"https://gamma-api.polymarket.com/markets/{market_id}"
        resp = await client.get(url, timeout=10.0)
        if resp.status_code == 200:
            return resp.json().get("bestAsk")
    except Exception:
        pass
    return None

async def run_source_audit():
    print("Extracting sources from logs...")
    
    # 1. Parse logs to map market_question -> source
    # The log looks like: 
    # 2026-02-28 11:20:30.123 | INFO     | ... | Director: Analyzing opportunity [Source: WHALE_TRACKER] on 'Who will win the NBA Finals?' (YES)
    sources_map = {}
    
    log_files = glob.glob("logs/autonomous*.log")
    for lf in log_files:
        print(f"Parsing {lf}...")
        try:
            with open(lf, "r", encoding="utf-8") as f:
                for line in f:
                    if "Director: Analyzing opportunity [Source:" in line:
                        match = re.search(r"\[Source: (.*?)\] on '(.*?)'", line)
                        if match:
                            src = match.group(1).strip()
                            q = match.group(2).strip()
                            if q and src:
                                sources_map[q.lower()] = src
        except Exception as e:
            print(f"Error reading {lf}: {e}")
            
    print(f"Found sources for {len(sources_map)} questions in logs.")
    
    # 2. Get WOULD_EXECUTE from DB
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
    
    # 3. Associate Source & Resolve
    resolved_markets = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        batch_size = 30
        for i in range(0, len(unique_markets), batch_size):
            batch = unique_markets[i:i + batch_size]
            tasks = [fetch_final_price(client, m["market_id"]) for m in batch]
            prices = await asyncio.gather(*tasks)
            
            for m, final in zip(batch, prices):
                if final is not None:
                    f = float(final)
                    if f >= 0.97 or f <= 0.03:
                        m["final_price"] = f
                        m["won"] = (f >= 0.97)
                        
                        # Edge net formula: score - ask - (spread * 0.5)
                        score = m.get("council_score", 0)
                        ask = m.get("best_ask", 0.5)
                        spread = m.get("spread", 0.0)
                        m["edge_net"] = score - ask - (spread * 0.5)
                        
                        # Map source
                        q_lower = m["market_question"].lower()
                        # Direct match
                        source = sources_map.get(q_lower, "UNKNOWN")
                        if source == "UNKNOWN":
                            # Try partial match (logs might truncate the quote)
                            for k, v in sources_map.items():
                                if k in q_lower or q_lower in k:
                                    source = v
                                    break
                                    
                        m["source"] = source
                        resolved_markets.append(m)

    # 4. Print stats
    print("\n" + "="*80)
    print("CONSULTA 1 — Accuracy por fuente de señal (RECONSTRUIDA DESDE LOS LOGS)")
    print("="*80)
    print(f"{'source':<25} | {'total':<6} | {'wins':<6} | {'accuracy':<8} | {'avg_c_score':<12} | {'avg_edge_net':<12}")
    print("-" * 80)
    
    groups = defaultdict(lambda: {"n": 0, "wins": 0, "score": 0.0, "edge": 0.0})
    for m in resolved_markets:
        src = m["source"]
        groups[src]["n"] += 1
        if m["won"]: groups[src]["wins"] += 1
        groups[src]["score"] += m["council_score"]
        groups[src]["edge"] += m["edge_net"]
        
    for src in sorted(groups.keys(), key=lambda x: (groups[x]["wins"]/groups[x]["n"] if groups[x]["n"] > 0 else 0), reverse=True):
        d = groups[src]
        if d["n"] > 0:
            acc = (d["wins"]/d["n"]*100)
            avg_s = d["score"] / d["n"]
            avg_e = d["edge"] / d["n"]
            print(f"{src:<25} | {d['n']:<6} | {d['wins']:<6} | {acc:>5.1f}%   | {avg_s:>12.3f} | {avg_e:>12.3f}")

    print("="*80)

if __name__ == "__main__":
    asyncio.run(run_source_audit())
