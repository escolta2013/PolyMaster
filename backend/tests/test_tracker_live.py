import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from app.engines.tracker.tracker import SmartMoneyTracker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_live_tracker():
    print("=" * 60)
    print("LIVE TRACKER INTEGRATION TEST")
    print("=" * 60)
    
    tracker = SmartMoneyTracker()
    
    try:
        # Run one cycle of the tracker
        # This will:
        # 1. Index top markets
        # 2. Discover traders from the first high-volume market
        # 3. Grade them and save to Supabase
        await tracker.update_smart_money_list()
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        # Verify Supabase data
        res = tracker.supabase.table("wallets").select("*").order("last_updated", desc=True).limit(5).execute()
        count = len(res.data)
        print(f"[OK] Successfully processed and stored {count} wallets in Supabase")
        
        if count > 0:
            print("\nLatest graded wallets:")
            for w in res.data:
                is_smart = "SMART" if w['is_smart_money'] else "Retail"
                print(f" - {w['address'][:10]}... | Grade: {w['grade']} | ROI: {w['roi']:.1%} | {is_smart}")
        
    except Exception as e:
        print(f"\n[FAIL] Tracker test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_live_tracker())
