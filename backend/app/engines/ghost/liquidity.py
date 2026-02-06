from app.core.client import PolyClient

class LiquidityManager:
    def __init__(self):
        self.client = PolyClient.get_instance()
        self.active_orders = []

    def place_spread_orders(self, market_id: str, spread_width: float = 0.05):
        """
        Places wide LIMIT orders on both sides (or just NO) to capture spread stats.
        TODO: Implement real order placement logic.
        """
        print(f" [Ghost] Placing liquidity orders for {market_id} width={spread_width}")
        # Logic:
        # 1. Get current mid
        # 2. Calc Bid = Mid - width
        # 3. Calc Ask = Mid + width
        # 4. client.create_order(...)
        return {"status": "orders_placed", "count": 2}

    def cancel_all(self):
        """
        Safety switch: Cancel all open orders managed by Ghost.
        """
        print(" [Ghost] Cancelling all orders...")
        # client.cancel_all()
        return {"status": "cancelled"}
