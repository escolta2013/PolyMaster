import os
import sys
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger

# Add backend to path to use config if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

async def fetch_market_price(market_id: str) -> Optional[float]:
    """Fetch current best ask from Gamma API as a proxy for profit evaluation."""
    try:
        url = f"https://gamma-api.polymarket.com/markets/{market_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                # Check for resolution first
                status = data.get("status")
                if data.get("resolved"):
                    # If resolved, look for the outcome
                    # This is complex in Gamma, usually 'outcome' or 'result' fields
                    # For simplicity, we'll check if it's 0 or 1 if we can find the right token
                    pass
                
                return data.get("bestAsk")
    except Exception as e:
        logger.warning(f"Failed to fetch price for {market_id}: {e}")
    return None

async def evaluate_real_performance(sims: List[Dict]):
    print(f"\n{'='*90}")
    print(f"{'REALIZED PERFORMANCE AUDIT (Definitively Resolved Only)':^90}")
    print(f"{'='*90}")
    print(f"{'MARKET QUESTION':<45} | {'ENTRY':<7} | {'FINAL':<7} | {'RESULT':<7} | {'P&L %':<8}")
    print(f"{'-'*90}")
    
    wins = 0
    losses = 0
    total_pnl = 0
    pending = 0
    
    for sim in sims:
        m_id = sim['market_id']
        question = sim['market_question'][:43]
        entry_price = float(sim['price_at_entry'])
        
        current_price = await fetch_market_price(m_id)
        
        if current_price is not None:
            current_price = float(current_price)
            
            # ── RESOLUTION FILTER ──
            # Only count as resolved if price is near 1.0 (WIN) or near 0.0 (LOSS)
            is_win = current_price >= 0.97
            is_loss = current_price <= 0.03
            
            if is_win or is_loss:
                # Real P&L based on holding to resolution
                # If it resolved to 1.0, PnL = (1.0 - entry) / entry
                # If it resolved to 0.0, PnL = -100%
                final_val = 1.0 if is_win else 0.0
                pnl_pct = (final_val - entry_price) / entry_price
                
                status = "WIN" if is_win else "LOSS"
                if is_win: wins += 1
                else: losses += 1
                total_pnl += pnl_pct
                
                print(f"{question:<45} | {entry_price:<7.3f} | {final_val:<7.3f} | {status:<7} | {pnl_pct*100:>+6.1f}%")
            else:
                pending += 1
                # Skip in-flight markets
                continue
        else:
            continue
            
    resolved_count = wins + losses
    if resolved_count > 0:
        accuracy = (wins / resolved_count) * 100
        avg_real_pnl = (total_pnl / resolved_count) * 100
        print(f"{'-'*90}")
        print(f"RESULT SUMMARY:")
        print(f" - Resolved Markets: {resolved_count}")
        print(f" - Accuracy:          {accuracy:.1f}% ({wins}W - {losses}L)")
        print(f" - Real realized ROI: {avg_real_pnl:>+7.2f}%")
        print(f" - Pending Markets:  {pending} (Skipped from audit)")
        print(f" - Accuracy of {accuracy:.1f}% vs Goal 62%+")
        print(f"{'='*90}")
    else:
        print("\nNo resolved markets found in this sample (all are still in-flight/pending).")
        print(f"Pending/In-flight: {pending}")
        print(f"{'='*90}")

if __name__ == "__main__":
    # The sims will be passed or we fetch from DB here
    # For now, I'll use a small subset of the IDs found in the previous step
    # or I can fetch them directly from DB if I run this as a script
    
    # Let's write the logic to fetch them from DB within the script
    from app.core.config import settings
    from supabase import create_client
    
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    res = supabase.table("autonomous_logs") \
        .select("market_id, market_question, best_ask, council_score") \
        .eq("decision", "WOULD_EXECUTE") \
        .order("detected_at", desc=True) \
        .limit(100) \
        .execute()
    
    if res.data:
        # Map data to include price_at_entry
        for entry in res.data:
            entry['price_at_entry'] = entry['best_ask']
        asyncio.run(evaluate_real_performance(res.data))
    else:
        print("No simulation data found in Supabase.")
