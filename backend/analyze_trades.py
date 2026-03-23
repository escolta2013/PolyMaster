import asyncio
import os
import sys
from datetime import datetime, timezone
from app.core.config import settings
from supabase import create_client

async def analyze():
    sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    # All trades
    res = sb.table("autonomous_logs").select("detected_at, correct, decision").execute()
    data = res.data
    
    if not data:
        print("No trades found in autonomous_logs.")
        return

    # March 16th cut-off
    cutoff = datetime(2026, 3, 16, tzinfo=timezone.utc)
    
    before = [r for r in data if datetime.fromisoformat(r['detected_at'].replace('Z', '+00:00')) < cutoff]
    after = [r for r in data if datetime.fromisoformat(r['detected_at'].replace('Z', '+00:00')) >= cutoff]
    
    def get_stats(rows, label):
        executed = [r for r in rows if r['decision'] in ['EXECUTED', 'WOULD_EXECUTE']]
        wins = [r for r in executed if r['correct'] == 'WIN']
        losses = [r for r in executed if r['correct'] == 'LOSS']
        pending = [r for r in executed if r['correct'] == 'PENDING']
        
        total_resolved = len(wins) + len(losses)
        accuracy = (len(wins) / total_resolved * 100) if total_resolved > 0 else 0
        
        print(f"--- {label} ---")
        print(f"Total Evaluated: {len(rows)}")
        print(f"Total Execution Decisions: {len(executed)}")
        print(f"Resolved: {total_resolved} ({len(wins)}W / {len(losses)}L)")
        print(f"Accuracy: {accuracy:.1f}%")
        print(f"Still Pending: {len(pending)}")
        print("-" * 20)

    get_stats(before, "BEFORE March 16 (Pre-Staleness Checks)")
    get_stats(after, "AFTER March 16 (Post-Staleness Checks)")
    get_stats(data, "OVERALL")

if __name__ == "__main__":
    asyncio.run(analyze())
