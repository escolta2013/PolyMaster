import os
import json
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
        
        # 1. Fetch top markets with high volume
        markets = self.indexer.get_top_markets(limit=10)
        
        for market in markets:
            m_id = market.get("id")
            question = market.get("question", "Unknown Market")
            volume = float(market.get("volume", 0))
            
            if not m_id: continue

            # Save market to DB
            try:
                self.supabase.table("tracked_markets").upsert({
                    "market_id": m_id,
                    "question": question,
                    "volume": volume,
                    "last_indexed": datetime.utcnow().isoformat()
                }).execute()
            except Exception as e:
                logger.error(f"Error upserting market {m_id}: {e}")

            # 2. Discover traders via high-volume trades
            # We use the Data API trades endpoint to find proxyWallets
            token_ids = []
            if "clobTokenIds" in market:
                import json
                token_ids = json.loads(market["clobTokenIds"]) if isinstance(market["clobTokenIds"], str) else market["clobTokenIds"]
            
            if token_ids:
                import requests
                # Scan trades for the first token
                try:
                    r = requests.get(f"https://data-api.polymarket.com/trades", params={"asset_id": token_ids[0], "limit": 50})
                    if r.status_code == 200:
                        traders = [t.get('proxyWallet') for t in r.json() if t.get('proxyWallet')]
                        # 3. Process each discovered wallet
                        self._process_potential_smart_money(list(set(traders)))
                except Exception as e:
                    logger.error(f"Error discovering traders for {m_id}: {e}")

    def _process_potential_smart_money(self, addresses: List[str]):
        """
        Analyze wallet addresses using Data API to calculate real performance metrics.
        """
        for addr in addresses:
            try:
                # Fetch positions from Data API
                positions = self.indexer.clob_client.get_user_positions(addr)
                
                if not positions or len(positions) == 0:
                    continue
                
                # Calculate real stats from positions
                total_trades = len(positions)
                total_realized_pnl = 0.0
                total_initial_value = 0.0
                total_volume = 0.0
                wins = 0
                
                for pos in positions:
                    realized = float(pos.get("realizedPnl", 0))
                    initial = float(pos.get("initialValue", 0)) 
                    # Volume heuristic: initial value + any realized value
                    # Data API doesn't give 'volume' directly per position, but initialValue is a good proxy for size
                    total_initial_value += initial
                    total_realized_pnl += realized
                    total_volume += initial # Simplistic volume
                    
                    # Heuristic for a 'win': positive realized PnL or positive current PnL
                    if realized > 0 or float(pos.get("cashPnl", 0)) > 0:
                        wins += 1
                
                # Calculate ROI
                roi = total_realized_pnl / total_initial_value if total_initial_value > 0 else 0
                win_rate = wins / total_trades if total_trades > 0 else 0
                
                stats = WalletStats(
                    address=addr,
                    roi=roi,
                    win_rate=win_rate,
                    total_trades=total_trades,
                    profit_usdc=total_realized_pnl,
                    volume_usdc=total_volume
                )
                
                grade = self.grader.grade_wallet(stats)
                is_smart = self.grader.is_smart_money(grade)
                
                # We upsert ALL graded wallets but flag smart money
                self.supabase.table("wallets").upsert({
                    "address": addr,
                    "grade": grade,
                    "roi": float(round(roi, 4)),
                    "win_rate": float(round(win_rate, 4)),
                    "total_trades": total_trades,
                    "profit_usdc": float(round(total_realized_pnl, 2)),
                    "volume_usdc": float(round(total_volume, 2)),
                    "is_smart_money": is_smart,
                    "last_updated": datetime.utcnow().isoformat()
                }).execute()
                
                if is_smart:
                    logger.info(f"SMART MONEY FOUND: {addr[:10]}... (Grade {grade}, ROI {roi:.1%})")
                    
            except Exception as e:
                logger.debug(f"Error processing wallet {addr[:10]}...: {e}")
