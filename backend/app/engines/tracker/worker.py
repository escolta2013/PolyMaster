import asyncio
import logging
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))
load_dotenv()

from backend.app.engines.tracker.tracker import SmartMoneyTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tracker_worker")

async def main_loop():
    """
    Persistent background worker to track Polymarket 'Smart Money'.
    """
    logger.info("Initializing PolyMaster Tracker Worker...")
    tracker = SmartMoneyTracker()
    
    interval = int(os.getenv("TRACKER_INTERVAL_SECONDS", "3600")) # 1 hour default
    
    logger.info(f"Worker started. Cycle interval: {interval}s")
    
    while True:
        try:
            start_time = datetime.now()
            logger.info(f"--- Cycle Start: {start_time.isoformat()} ---")
            
            await tracker.update_smart_money_list()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"--- Cycle Complete: {end_time.isoformat()} (Took {duration:.2f}s) ---")
            
            logger.info(f"Sleeping for {interval}s...")
            await asyncio.sleep(interval)
            
        except Exception as e:
            logger.error(f"Critical error in worker loop: {e}")
            logger.info("Retrying in 60s...")
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")
