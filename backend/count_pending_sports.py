import os, sys, httpx, asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict

# Fix Windows console encoding
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv

# Path to .env (must be loaded BEFORE importing settings)
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

from app.core.config import settings
from supabase import create_client

async def fetch_market_info(market_id: str) -> Optional[Dict]:
    """Consulta Gamma API para obtener info del mercado."""
    try:
        url = f"https://gamma-api.polymarket.com/markets/{market_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None

def is_sports(q: str) -> bool:
    ql = q.lower()
    # Traditional sports keywords
    sports_kw = [
        "nba", "nhl", "nfl", "mlb", "soccer", "football", "basketball", "hockey", 
        "tennis", "winner on 2026-", "match winner", "total goals", "points", 
        "rebound", "assist", "spread", "over/under", "o/u"
    ]
    # Exclude eSports explicitly as requested in previous contexts if necessary, 
    # but "sports markets" usually refers to the ones the bot *is* trading or monitoring.
    esports_kw = ["dota 2", "counter-strike", "valorant", "lol:", "league of legends"]
    
    if any(k in ql for k in esports_kw):
        return False
    return any(k in ql for k in sports_kw)

async def count_pending():
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    # Fetch unique WOULD_EXECUTE or EXECUTED markets
    res = supabase.table("autonomous_logs") \
        .select("market_id, market_question, decision, detected_at") \
        .in_("decision", ["WOULD_EXECUTE", "EXECUTED"]) \
        .order("detected_at", desc=True) \
        .execute()

    rows = res.data or []
    
    # Unique by market_id
    seen_ids = set()
    unique_active = []
    for r in rows:
        if r["market_id"] not in seen_ids:
            unique_active.append(r)
            seen_ids.add(r["market_id"])

    print(f"Total mercados únicos en logs (activos): {len(unique_active)}")
    
    now_utc = datetime.now(timezone.utc)
    # Tonight = ends before tomorrow morning 12:00 UTC (prox 12h)
    tonight_limit = now_utc + timedelta(hours=14) 
    
    pending_sports_tonight = []
    
    tasks = [fetch_market_info(m["market_id"]) for m in unique_active]
    market_infos = await asyncio.gather(*tasks)
    
    for m_log, m_info in zip(unique_active, market_infos):
        if not m_info:
            continue
            
        q = m_info.get("question", "")
        best_ask = m_info.get("bestAsk")
        
        # Check if resolved (0 or 1)
        if best_ask is not None:
            ask_val = float(best_ask)
            if ask_val <= 0.01 or ask_val >= 0.99:
                continue # Resolved
        
        # Check end date
        end_date_iso = m_info.get("end_date_iso") or m_info.get("endDate")
        if end_date_iso:
            try:
                end_dt = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=timezone.utc)
                
                # If it ends today (Mar 1) or very early tomorrow (Mar 2)
                if end_dt < tonight_limit:
                    if is_sports(q):
                        pending_sports_tonight.append({
                            "question": q,
                            "end_date": end_dt,
                            "id": m_info.get("id"),
                            "cat": "SPORTS"
                        })
                    else:
                        print(f"DEBUG: Other ending tonight: {q}")
            except:
                pass

    print(f"\nMercados deportivos pendientes de resolver esta noche (Mar 1/2): {len(pending_sports_tonight)}")
    for m in pending_sports_tonight:
        print(f"- [{m['end_date'].strftime('%H:%M UTC')}] {m['question']}")

if __name__ == "__main__":
    asyncio.run(count_pending())
