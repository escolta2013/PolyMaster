
import os, sys, glob, re, asyncio, httpx, json

sys.path.insert(0, os.path.abspath("."))
from app.core.config import settings
from supabase import create_client

def get_fine_category(q: str) -> str:
    ql = q.lower()
    if any(k in ql for k in ["temperature", "weather", "seoul", "degrees"]): return "WEATHER"
    if any(k in ql for k in ["nba", "basketball", "lebron", "curry"]): return "NBA"
    if any(k in ql for k in ["tennis", "atp", "wta", "open", "handicap"]): 
        if "tennis" in ql or any(x in ql for x in ["atp", "wta"]): return "TENNIS"
    if any(k in ql for k in ["bitcoin", "eth ", "ethereum", "crypto", "price of"]): return "CRYPTO"
    if any(k in ql for k in ["soccer", "football", "champions league", "premier league"]): return "SOCCER"
    return "OTHER"

async def run_db_update():
    print("Extracting sources from logs...")
    sources_map = {}
    log_files = glob.glob("logs/autonomous*.log")
    for lf in log_files:
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
        except Exception:
            pass
            
    # Connect
    s = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    print("Fetching WOULD_EXECUTE trades to update...")
    all_rows = []
    offset = 0
    limit = 1000
    while True:
        res = s.table('autonomous_logs').select('id, market_question, best_ask, council_score, spread, source').eq('decision', 'WOULD_EXECUTE').range(offset, offset + limit - 1).execute()
        if not res.data: break
        all_rows.extend(res.data)
        if len(res.data) < limit: break
        offset += limit
        
    print(f"Total rows to update: {len(all_rows)}")
    batch_size = 50
    updated_count = 0
    
    for r in all_rows:
        q_lower = r["market_question"].lower()
        
        # Determine source
        source = sources_map.get(q_lower, "UNKNOWN")
        if source == "UNKNOWN":
            for k, v in sources_map.items():
                if k in q_lower or q_lower in k:
                    source = v
                    break
        
        # Just update source (Supabase autonomous_logs only has source. Category/edge_net can be kept in memory or we can add them to table too, but user only added 'source' DDL)
        # Actually user asked for source. Let's update it.
        if r.get("source") != source:
            s.table('autonomous_logs').update({"source": source}).eq("id", r["id"]).execute()
            updated_count += 1
            if updated_count % 50 == 0:
                print(f"Updated {updated_count} rows...")
                
    print(f"Done! Retroactively updated {updated_count} rows with their source.")

if __name__ == "__main__":
    asyncio.run(run_db_update())
