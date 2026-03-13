import asyncio
import os
import sys
from datetime import datetime
from loguru import logger

# Add backend to path for module resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.core.config import settings
from app.core.logging import setup_logging
from app.engines.tracker.tracker import SmartMoneyTracker
from app.engines.tracker.cluster_detector import ClusterDetector

async def cluster_scan_loop(detector: ClusterDetector):
    """Frequent loop to check for wallet convergence."""
    # We could move this to settings later if needed
    interval = int(os.getenv("CLUSTER_SCAN_INTERVAL_SECONDS", "300")) 
    logger.info(f"Cluster detector task started. Interval: {interval}s")
    
    while True:
        try:
            logger.info("Executing periodic cluster scan...")
            await detector.scan_for_clusters()
            await asyncio.sleep(interval)
        except Exception as e:
            logger.error(f"Error in cluster scan task: {e}")
            await asyncio.sleep(60)

async def main_loop():
    """Persistent background worker to track Polymarket 'Smart Money'."""
    logger.info("Initializing PolyMaster Tracker Engine Worker...")
    
    tracker = SmartMoneyTracker()
    detector = ClusterDetector()
    
    # Start the cluster scanner as a separate task
    asyncio.create_task(cluster_scan_loop(detector))

    # Phase 4.3: Start Spike Trigger (Flash Engine)
    try:
        from app.engines.flash.trigger import spike_monitor
        asyncio.create_task(spike_monitor.monitor_stream())
        logger.success("⚡ Flash Engine Spike Trigger Activated")
    except Exception as e:
        logger.error(f"Failed to start Flash Trigger: {e}")
    
    sync_interval = int(os.getenv("TRACKER_INTERVAL_SECONDS", "3600"))
    logger.info(f"Sync worker active. Cycle interval: {sync_interval}s")
    
    while True:
        try:
            start_time = datetime.now()
            logger.info(f"=== Sync Cycle Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ===")
            
            await tracker.update_smart_money_list()
            
            # Run a cluster scan immediately after sync
            await detector.scan_for_clusters()
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.success(f"=== Sync Cycle Complete (Took {duration:.2f}s) ===")
            
            logger.info(f"Worker standby for {sync_interval}s...")
            await asyncio.sleep(sync_interval)
            
        except Exception as e:
            logger.error(f"Critical error in main sync loop: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.warning("Worker terminated by user.")
