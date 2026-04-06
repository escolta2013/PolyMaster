from typing import Optional
from app.core.client import PolyClient
from app.engines.ghost.order_manager import OrderManager
from app.engines.ghost.risk_manager import RiskManager
import logging

logger = logging.getLogger("LiquidityManager")

class LiquidityManager:
    """
    Ghost Liquidity Manager: Implements 'Liquidity Grinder' and 'NEH' execution.
    """
    def __init__(self):
        self.client = PolyClient.get_instance()
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager()
        self.active_orders = {} # market_id: [order_ids]
        self.simulation_mode = True 
        self.target_spread = 0.02

    def set_execution_mode(self, simulation: bool):
        self.simulation_mode = simulation
        self.risk_manager.simulation_mode = simulation
        logger.info(f"Ghost Execution Mode set to: {'SIMULATION' if simulation else 'LIVE'}")

    async def place_spread_orders(self, market_id: str, token_id: str, spread_width: Optional[float] = None, size: float = 10.0):
        """
        Calculates and places LIMIT orders. 
        If spread_width is None, it uses the Adaptive Spread logic.
        """
        try:
            # 1. Risk Check
            if not self.risk_manager.check_exposure(size, 0):
                return {"status": "error", "reason": "Risk Limit Reached"}

            # 2. Get Price Intelligence
            intel = await self.client.get_orderbook(token_id)
            mid = intel.get("midpoint", 0.5)
            
            # 3. Handle Adaptive Spread (Inspired by poly-trading-skills)
            if spread_width is None:
                volatility = await self.client.get_market_volatility(token_id)
                # Base spread + volatility multiplier (e.g., 2% base + 10x volatility)
                base_spread = 0.02
                adaptive_spread = base_spread + (volatility * 15)
                spread_width = min(adaptive_spread, 0.10) # Cap at 10%
                logger.info(f" [Ghost] Adaptive Spread for {market_id}: {spread_width:.2%} (Vol: {volatility:.5f})")
            
            # 4. Calc Bid and Ask
            bid_price = round(mid * (1 - spread_width/2), 3)
            ask_price = round(mid * (1 + spread_width/2), 3)
            
            if bid_price >= ask_price:
                return {"status": "error", "reason": "Invalid spread calculation"}

            logger.info(f" [Ghost] TACTICAL GRINDER: {'[SIM]' if self.simulation_mode else '[LIVE]'} Placing Bid @ ${bid_price}, Ask @ ${ask_price} for {market_id}")
            
            orders_info = [
                {"side": "BUY", "price": bid_price, "size": size},
                {"side": "SELL", "price": ask_price, "size": size}
            ]

            if self.simulation_mode:
                return {
                    "status": "simulated",
                    "strategy": "Adaptive Grinder",
                    "market": market_id,
                    "volatility": volatility if 'volatility' in locals() else 0,
                    "spread_used": spread_width,
                    "orders": orders_info
                }

            # 5. Real Execution
            placed_order_ids = []
            for o in orders_info:
                res = self.order_manager.create_and_post_order(
                    token_id=token_id,
                    price=o["price"],
                    size=o["size"],
                    side=o["side"]
                )
                if res["status"] == "success":
                    placed_order_ids.append(res["order_id"])
            
            self.active_orders[market_id] = placed_order_ids

            return {
                "status": "active",
                "strategy": "Adaptive Grinder",
                "market": market_id,
                "order_ids": placed_order_ids
            }
        except Exception as e:
            logger.error(f"Error in place_spread_orders: {e}")
            return {"status": "error", "reason": str(e)}

    def place_neh_order(self, market_id: str, token_id: str, size: float = 50.0):
        """
        Specialized 'Nothing Ever Happens' order (Systematic NO).
        Places a limit buy on the NO token or limit sell on the YES token.
        """
        # For simplicity, we sell YES shares (betting against the hype)
        return self.order_manager.create_and_post_order(
            token_id=token_id,
            price=0.85, # Aggressive sell on over-optimistic YES
            size=size,
            side="SELL"
        ) if not self.simulation_mode else {"status": "simulated", "strategy": "NEH"}

    def cancel_all(self):
        logger.info(" [Ghost] Cancelling all orders...")
        if self.simulation_mode:
            self.active_orders = {}
            return {"status": "cancelled", "mode": "simulation"}
            
        res = self.order_manager.cancel_all_orders()
        self.active_orders = {}
        return {"status": "cancelled", "response": res}
