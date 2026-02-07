from app.core.client import PolyClient
from app.engines.ghost.order_manager import OrderManager
import logging

logger = logging.getLogger("LiquidityManager")

class LiquidityManager:
    def __init__(self):
        self.client = PolyClient.get_instance()
        self.order_manager = OrderManager()
        self.active_orders = {} # market_id: [order_ids]
        self.simulation_mode = True # Default to safe mode

    def set_execution_mode(self, simulation: bool):
        self.simulation_mode = simulation
        logger.info(f"Ghost Execution Mode set to: {'SIMULATION' if simulation else 'LIVE'}")

    def place_spread_orders(self, market_id: str, token_id: str, spread_width: float = 0.02, size: float = 10.0):
        """
        Calculates and places wide LIMIT orders to capture spread.
        """
        try:
            # 1. Get current mid price
            mid_data = self.client.get_midpoint(token_id)
            mid = float(mid_data.get('mid', 0.5))
            
            # 2. Calc Bid (Buy low) and Ask (Sell high)
            bid_price = round(mid * (1 - spread_width/2), 3)
            ask_price = round(mid * (1 + spread_width/2), 3)
            
            # 3. Validation
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
                    "strategy": "Liquidity Grinder",
                    "market": market_id,
                    "orders": orders_info
                }

            # 4. Real Execution
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
                "strategy": "Liquidity Grinder",
                "market": market_id,
                "order_ids": placed_order_ids
            }
        except Exception as e:
            logger.error(f"Error in place_spread_orders: {e}")
            return {"status": "error", "reason": str(e)}

    def cancel_all(self):
        """
        Safety switch: Cancel all open orders managed by Ghost.
        """
        logger.info(" [Ghost] Cancelling all orders...")
        if self.simulation_mode:
            self.active_orders = {}
            return {"status": "cancelled", "mode": "simulation"}
            
        res = self.order_manager.cancel_all_orders()
        self.active_orders = {}
        return {"status": "cancelled", "response": res}
