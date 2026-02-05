import os
import logging
from datetime import datetime
from typing import List
from supabase import create_client, Client
from .indexer import PolymarketIndexer
from .grader import WalletGrader, WalletStats

logger = logging.getLogger(__name__)

class SmartMoneyTracker:
    """
    Orchestrator for the Smart Money Tracking engine.
    1. Indexes markets
    2. Identifies active traders
    3. Grades wallets
    4. Persists 'Smart Money' to Supabase
    """

    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        self.supabase: Client = create_client(url, key)
        self.indexer = PolymarketIndexer()
        self.grader = WalletGrader()

    async def update_smart_money_list(self):
        """
        Main loop to refresh the smart money database.
        """
        logger.info("Starting Smart Money update cycle...")
        
        # 1. Fetch top markets
        markets = self.indexer.get_top_markets(limit=5)
        
        for market in markets:
            m_id = market.get("id")
            question = market.get("title", "Unknown Market")
            volume = float(market.get("volume", 0))
            
            # Save market to DB
            self.supabase.table("tracked_markets").upsert({
                "market_id": m_id,
                "question": question,
                "volume": volume,
                "last_indexed": datetime.utcnow().isoformat()
            }).execute()

            # 2. Find active traders (simulated for now)
            # In production, this would call CLOB API
            traders = self.indexer.get_market_traders(m_id)
            
            # Placeholder: Let's assume we found some interesting wallets
            # This is where the heavy lifting of history analysis happens
            self._process_potential_smart_money(traders)

    def _process_potential_smart_money(self, addresses: List[str]):
        for addr in addresses:
            # Simulate fetching history and calculating stats
            # In production: Fetch from Covalent/Debank/Polymarket History
            stats = WalletStats(
                address=addr,
                roi=0.25, # Example
                win_rate=0.70,
                total_trades=100,
                profit_usdc=5000.0
            )
            
            grade = self.grader.grade_wallet(stats)
            is_smart = self.grader.is_smart_money(grade)
            
            if is_smart:
                self.supabase.table("wallets").upsert({
                    "address": addr,
                    "grade": grade,
                    "roi": stats.roi,
                    "win_rate": stats.win_rate,
                    "total_trades": stats.total_trades,
                    "profit_usdc": stats.profit_usdc,
                    "is_smart_money": True,
                    "last_updated": datetime.utcnow().isoformat()
                }).execute()
                logger.info(f"Found and saved Smart Money: {addr} (Grade {grade})")
