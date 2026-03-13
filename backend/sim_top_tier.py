
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

def is_top_tier(q: str) -> bool:
    ql = q.lower()
    # Weather and Crypto are our gold mines
    is_weather = any(k in ql for k in ["temperature", "weather", "seoul", "degrees"])
    is_crypto = any(k in ql for k in ["bitcoin", "eth ", "ethereum", "crypto", "price of"])
    return is_weather or is_crypto

async def run_top_tier_simulation():
    print("Simulando Especialización: Solo WEATHER y CRYPTO con $200 USD...")
    s = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    all_rows = []
    offset = 0
    limit = 1000
    while True:
        res = s.table('autonomous_logs').select('*').eq('decision', 'WOULD_EXECUTE').order('detected_at', desc=False).range(offset, offset + limit - 1).execute()
        if not res.data: break
        all_rows.extend(res.data)
        if len(res.data) < limit: break
        offset += limit

    seen = {}
    for r in all_rows:
        mid = r["market_id"]
        if mid not in seen:
            seen[mid] = r
    
    unique_markets_sorted = sorted(seen.values(), key=lambda x: x["detected_at"])
    
    bankroll = 200.0
    bet_per_trade = 10.0 
    
    wins = 0
    losses = 0
    total_invested = 0.0

    async with httpx.AsyncClient() as client:
        batch_size = 30
        for i in range(0, len(unique_markets_sorted), batch_size):
            batch = unique_markets_sorted[i:i + batch_size]
            tasks = [fetch_final_price(client, m["market_id"]) for m in batch]
            prices = await asyncio.gather(*tasks)
            
            for m, final in zip(batch, prices):
                q = m["market_question"]
                if not is_top_tier(q) or final is None:
                    continue
                
                entry = float(m.get("best_ask") or 0.5)
                f = float(final)
                
                if f >= 0.97: # WIN
                    profit = (bet_per_trade / entry) - bet_per_trade
                    bankroll += profit
                    total_invested += bet_per_trade
                    wins += 1
                elif f <= 0.03: # LOSS
                    bankroll -= bet_per_trade
                    total_invested -= bet_per_trade
                    losses += 1

    print("="*60)
    print(f"{'SIMULACIÓN: ESPECIALISTA TOP-TIER (WEATHER & CRYPTO)':^60}")
    print("="*60)
    print(f"Bankroll Inicial:        $200.00 USD")
    print(f"Stake por Trade:         $ 10.00 USD")
    print("-" * 60)
    print(f"Mercados Analizados:     {wins + losses}")
    print(f"  - Aciertos (Wins):     {wins}")
    print(f"  - Fallos (Losses):     {losses}")
    print(f"  - Accuracy:           {(wins/(wins+losses)*100):.1f}%" if (wins+losses)>0 else "0%")
    print("-" * 60)
    print(f"Ganancia Neta:           ${(bankroll - 200):.2f} USD")
    print(f"BANKROLL FINAL:          ${bankroll:.2f} USD")
    print(f"ROI sobre Bankroll:      {((bankroll - 200)/200 * 100):+.2f}%")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_top_tier_simulation())
