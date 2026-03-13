
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
    if any(k in ql for k in esports_kw): return "EXCLUIDA"
    if ("win on 2026-" in ql and "both teams" not in ql and "o/u" not in ql): return "EXCLUIDA"
    if any(k in ql for k in ["close above $", "nvidia", "bitcoin be between", "nvda"]): return "EXCLUIDA"
    return "MANTENIDA"

async def run_simulation_200usd():
    print("Iniciando simulación financiera con $200 USD (Bankroll inicial)...")
    s = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    # Obtener TODOS los WOULD_EXECUTE con paginación
    all_rows = []
    offset = 0
    limit = 1000
    while True:
        res = s.table('autonomous_logs').select('*').eq('decision', 'WOULD_EXECUTE').order('detected_at', desc=False).range(offset, offset + limit - 1).execute()
        if not res.data: break
        all_rows.extend(res.data)
        if len(res.data) < limit: break
        offset += limit

    # Agrupar por mercado único (mantenemos el precio de entrada más antiguo)
    seen = {}
    for r in all_rows:
        mid = r["market_id"]
        if mid not in seen:
            seen[mid] = r
    
    unique_markets_sorted = sorted(seen.values(), key=lambda x: x["detected_at"])
    
    bankroll = 200.0
    bet_per_trade = 10.0 # Apostamos $10 USD por trade (Fixed stake)
    
    total_invested = 0.0
    total_won_lost = 0.0
    max_drawdown = 0.0
    peak_bankroll = 200.0
    
    wins = 0
    losses = 0
    pending = 0

    async with httpx.AsyncClient() as client:
        batch_size = 20
        for i in range(0, len(unique_markets_sorted), batch_size):
            batch = unique_markets_sorted[i:i + batch_size]
            tasks = [fetch_final_price(client, m["market_id"]) for m in batch]
            prices = await asyncio.gather(*tasks)
            
            for m, final in zip(batch, prices):
                q = m["market_question"]
                entry = float(m.get("best_ask") or 0.5)
                # Solo simulamos la categoría MANTENIDA para ver el resultado real post-filtros
                if categorize(q) != "MANTENIDA":
                    continue
                
                if final is None:
                    pending += 1
                    continue
                
                f = float(final)
                total_invested += bet_per_trade
                
                if f >= 0.97: # WIN
                    # Profit = (Stake / Entry) - Stake
                    # Ejemplo: $10 / 0.50 = 20 shares (valor final $20). Profit = $10.
                    profit = (bet_per_trade / entry) - bet_per_trade
                    bankroll += profit
                    total_won_lost += profit
                    wins += 1
                elif f <= 0.03: # LOSS
                    bankroll -= bet_per_trade
                    total_won_lost -= bet_per_trade
                    losses += 1
                else:
                    pending += 1
                
                if bankroll > peak_bankroll:
                    peak_bankroll = bankroll
                dd = (peak_bankroll - bankroll)
                if dd > max_drawdown:
                    max_drawdown = dd

    print("="*60)
    print(f"{'SIMULACIÓN FINANCIERA POLYMASTER ($200 BANKROLL)':^60}")
    print("="*60)
    print(f"Bankroll Inicial:        $200.00 USD")
    print(f"Stake Fijo por Trade:    $ 10.00 USD")
    print(f"Categoría Simulada:      MANTENIDA (Core Strategy)")
    print("-" * 60)
    tot_res = wins + losses
    acc = (wins/tot_res*100) if tot_res>0 else 0
    print(f"Mercados Analizados:     {len(batch)}")
    print(f"Mercados Resueltos:      {tot_res}")
    print(f"  - Aciertos (Wins):     {wins}")
    print(f"  - Fallos (Losses):     {losses}")
    print(f"  - Accuracy Real:      {acc:.1f}%")
    print("-" * 60)
    print(f"Capital Invertido Total: ${total_invested:,.2f} USD")
    print(f"Ganancia/Pérdida Neta:   {total_won_lost:+.2f} USD")
    print(f"BANKROLL FINAL:          ${bankroll:,.2f} USD")
    roi_bankroll = ((bankroll - 200)/200 * 100)
    print(f"ROI sobre Bankroll:      {roi_bankroll:+.2f}%")
    print(f"Drawdown Máximo:         ${max_drawdown:,.2f} USD")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_simulation_200usd())
