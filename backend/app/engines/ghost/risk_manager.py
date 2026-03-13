import logging
from datetime import datetime
from typing import Dict, List
from app.core.client import PolyClient
from .order_manager import OrderManager

logger = logging.getLogger("RiskManager")

class RiskManager:
    """
    Ghost Risk Manager: Handles Stop-Loss, Take-Profit, and Exposure Limits.
    Derived from 'Plan Maestro.docx' and 'Dominio y Estrategias.docx'.
    """
    def __init__(self, simulation_mode: bool = True):
        self.client = PolyClient.get_instance()
        self.order_manager = OrderManager()
        self.simulation_mode = simulation_mode
        self.risk_params = {
            "stop_loss_limit": 0.15,      # 15% Max loss
            "take_profit_target": 0.25,   # 25% Goal
            "position_cap_amount": 100.00 # Max USDC per market
        }
        self.active_risk_monitoring = {} # market_id -> entry_price

    def set_risk_params(self, params: Dict):
        self.risk_params.update(params)
        logger.info(f"Risk parameters updated: {self.risk_params}")

    def check_exposure(self, proposed_size_usdc: float, current_exposure: float) -> bool:
        """Verify if adding to position exceeds the cap."""
        if (proposed_size_usdc + current_exposure) > self.risk_params["position_cap_amount"]:
            logger.warning(f"Position cap exceeded! Limit: {self.risk_params['position_cap_amount']}, Proposed Total: {proposed_size_usdc + current_exposure}")
            return False
        return True

    def monitor_positions(self, positions: List[Dict]):
        """
        Scan active positions for SL/TP triggers.
        """
        for pos in positions:
            market_id = pos.get("conditionId")
            token_id = pos.get("asset")
            size = float(pos.get("size", 0))
            current_price = float(pos.get("price", 0.5)) 
            
            # Simple heuristic: if we don't have entry price, we can't calc SL/TP accurately.
            # In a real app, we'd store entry prices in a DB.
            entry_price = self.active_risk_monitoring.get(market_id, 0.5) 
            
            pnl_percent = (current_price - entry_price) / entry_price if entry_price > 0 else 0
            
            # Check Stop Loss
            if pnl_percent <= -self.risk_params["stop_loss_limit"]:
                logger.info(f" [CRITICAL] Stop-Loss Triggered for {market_id}! PnL: {pnl_percent*100:.1f}%")
                self.emergency_exit(token_id, size)
            
            # Check Take Profit
            elif pnl_percent >= self.risk_params["take_profit_target"]:
                logger.info(f" [TAKE PROFIT] Target reached for {market_id}! PnL: {pnl_percent*100:.1f}%")
                self.emergency_exit(token_id, size)

    def emergency_exit(self, token_id: str, size: float):
        """Sell all shares immediately."""
        logger.info(f"Executing Emergency Exit for token {token_id}...")
        if self.simulation_mode:
            logger.info(f"[SIM] Would sell {size} shares of {token_id}")
            return
        
        # Determine side (if we hold YES/NO, we need to sell)
        # For simplicity, we assume we are selling the token we hold
        # In Gamma, asset is the token ID.
        self.order_manager.create_and_post_order(
            token_id=token_id,
            price=0.01, # Market sell (aggresive low price)
            size=size,
            side="SELL"
        )
