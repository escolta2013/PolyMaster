from loguru import logger
from typing import Dict, List, Optional
import asyncio
from datetime import datetime, timezone
from app.core.client import PolyClient
from app.engines.ghost.order_manager import OrderManager

class RewardsManager:
    """
    Rewards Manager (The Grinder): 
    Monitors reward-eligible markets and maintains orders within the 
    'Scoring Range' to farm passive USDC rewards.
    
    Inspired by 'poly-trading-skills' Rewards Optimization patterns.
    """
    
    def __init__(self):
        self.client = PolyClient.get_instance()
        self.order_manager = OrderManager()
        self.active_farms = {} # market_id: { "buy_id": str, "sell_id": str, "token_id": str }
        self.target_offset = 0.03 # 3 cents from mid for better scoring safety
        self.max_offset = 0.045 # Threshold to move (4.5 cents)

    async def scan_and_farm(self, limit: int = 3):
        """
        Finds markets with rewards and initiates farming.
        """
        from app.engines.tracker.indexer import PolymarketIndexer
        indexer = PolymarketIndexer()
        
        logger.info("Farming: Scanning for reward-eligible markets...")
        markets = await indexer.get_reward_markets(limit=limit)
        
        for m in markets:
            m_id = m.get("id")
            # Usually rewards apply to the whole market, we pick the first token (YES)
            token_ids = m.get("clobTokenIds", [])
            if not token_ids or m_id in self.active_farms:
                continue
                
            token_id = token_ids[0] # Typically YES token
            logger.success(f"Farming: Initiating farm for '{m.get('question')[:30]}...' ({m_id})")
            await self.place_scoring_orders(m_id, token_id)

    async def place_scoring_orders(self, market_id: str, token_id: str, size: float = 100.0):
        """
        Places a BUY and SELL order within the scoring range.
        """
        try:
            intel = await self.client.get_orderbook(token_id)
            mid = intel.get("midpoint", 0.5)
            
            buy_price = round(mid - self.target_offset, 3)
            sell_price = round(mid + self.target_offset, 3)
            
            # Constraints: Prices must be between 0.001 and 0.999
            buy_price = max(0.005, buy_price)
            sell_price = min(0.995, sell_price)
            
            logger.info(f"Farming: Placing Scoring orders for {market_id} around {mid:.3f}")
            
            # Place BUY
            res_buy = self.order_manager.create_and_post_order(
                token_id=token_id, price=buy_price, size=size, side="BUY"
            )
            
            # Place SELL
            res_sell = self.order_manager.create_and_post_order(
                token_id=token_id, price=sell_price, size=size, side="SELL"
            )
            
            if res_buy["status"] == "success" and res_sell["status"] == "success":
                self.active_farms[market_id] = {
                    "token_id": token_id,
                    "buy_id": res_buy["order_id"],
                    "sell_id": res_sell["order_id"],
                    "midpoint_at_entry": mid
                }
                logger.success(f"Farming: Orders placed for {market_id}. BUY: {res_buy['order_id']}, SELL: {res_sell['order_id']}")
            else:
                # Cleanup if one fails
                if res_buy.get("order_id"): self.order_manager.cancel_order(res_buy["order_id"])
                if res_sell.get("order_id"): self.order_manager.cancel_order(res_sell["order_id"])
                
        except Exception as e:
            logger.error(f"Farming: Failed to place orders for {market_id}: {e}")

    async def monitor_active_farms(self):
        """
        Maintains orders within the scoring range. 
        If midpoint moves > 4.5 cents, cancel and replace.
        """
        if not self.active_farms:
            return
            
        logger.info(f"Farming: Monitoring {len(self.active_farms)} active reward positions...")
        
        # We need to copy keys because we might modify dict during iteration
        for m_id in list(self.active_farms.keys()):
            farm = self.active_farms[m_id]
            token_id = farm["token_id"]
            
            try:
                # 1. Get fresh price
                intel = await self.client.get_orderbook(token_id)
                current_mid = intel.get("midpoint")
                if not current_mid: continue
                
                # 2. Check scoring for both orders
                is_buy_scoring = self.order_manager.is_order_scoring(farm["buy_id"])
                is_sell_scoring = self.order_manager.is_order_scoring(farm["sell_id"])
                
                # 3. Decision logic: If EITHER is not scoring, or mid drifted too far
                drift = abs(current_mid - farm["midpoint_at_entry"])
                
                if not is_buy_scoring or not is_sell_scoring or drift > 0.04:
                    logger.warning(f"Farming: Midpoint drift ({drift:.3f}) or scoring loss for {m_id}. Rebalancing...")
                    
                    # Cancel existing
                    self.order_manager.cancel_order(farm["buy_id"])
                    self.order_manager.cancel_order(farm["sell_id"])
                    
                    # Remove from tracking
                    del self.active_farms[m_id]
                    
                    # Re-place
                    await self.place_scoring_orders(m_id, token_id)
                else:
                    logger.debug(f"Farming: Market {m_id} is still scoring (Drift: {drift:.4f})")
                    
            except Exception as e:
                logger.error(f"Farming: Error monitoring {m_id}: {e}")

rewards_manager = RewardsManager()
