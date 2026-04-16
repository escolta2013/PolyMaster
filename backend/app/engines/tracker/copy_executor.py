"""
Copy Executor — Phase 1 Core Feature

Enables users to replicate ("copy") the trades of identified smart-money
wallets.  The executor fetches the target wallet's active position on a
given market, mirrors the trade direction (BUY side for the same outcome),
and posts an order through the authenticated CLOB client.

Safety features:
  - Max position size cap (per trade)
  - Max daily exposure cap
  - Simulation mode toggle
  - Order log persisted to Supabase
"""

import os
import logging
from datetime import datetime, date, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass
from py_clob_client.clob_types import OrderArgs, OrderType
from app.core.client import PolyClient
from app.core.config import settings

logger = logging.getLogger("CopyExecutor")


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class CopyTradeRequest:
    """Input for a copy-trade action."""
    user_id: str                # ID of the user executing the copy
    source_wallet: str          # wallet address being copied
    token_id: str               # the CLOB token to trade
    market_id: str              # reference for logging
    market_question: str        # human-readable label
    outcome: str                # "YES" or "NO"
    price: float                # limit price (from orderbook mid)
    size_usdc: float            # amount in USDC to invest


@dataclass
class CopyTradeResult:
    """Output of a copy-trade attempt."""
    status: str                 # "success" | "simulated" | "error"
    order_id: Optional[str] = None
    message: str = ""
    trade: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class CopyExecutor:
    """
    Handles one-click copy-trading from the dashboard.

    Configuration (env vars or defaults):
      COPY_MAX_PER_TRADE    max USDC per single order (default: 100)
      COPY_MAX_DAILY        max total USDC per day    (default: 500)
      COPY_SIMULATION       "true" to paper-trade     (default: "true")
    """

    def __init__(self):
        self.client = PolyClient.get_instance()
        self.max_per_trade = settings.COPY_MAX_PER_TRADE
        self.max_daily = settings.COPY_MAX_DAILY
        self.simulation = settings.COPY_SIMULATION

        # Daily exposure tracker  { "YYYY-MM-DD": total_usdc }
        self._daily_spent: Dict[str, float] = {}

        # Supabase (optional — for persisting trade log)
        self._supabase = None
        try:
            from supabase import create_client
            url = settings.SUPABASE_URL
            key = settings.SUPABASE_KEY
            if url and key:
                self._supabase = create_client(url, key)
        except Exception:
            pass

        # Sync persistent state
        if self._supabase:
            self._sync_daily_spent()

    def _sync_daily_spent(self):
        """Recover today's spend from Supabase to enforce limits across restarts."""
        try:
            today = date.today().isoformat()
            # Sum up 'usdc' column for today's trades
            # Note: storing dates as ISO strings in 'timestamp' column
            # We filter for timestamp starting with today's date
            resp = self._supabase.table("copy_trades").select("usdc") \
                .gte("timestamp", today).execute()
            
            total = sum(item['usdc'] for item in (resp.data or []))
            self._daily_spent[today] = total
            if total > 0:
                logger.info(f"Restored daily spend: ${total:.2f} (Limit: ${self.max_daily})")
        except Exception as e:
            logger.warning(f"Failed to sync daily spend: {e}")

    # ---- public API ---------------------------------------------------------

    async def execute_copy(self, req: CopyTradeRequest) -> CopyTradeResult:
        """
        Validate and execute (or simulate) a copy trade.
        """
        from app.engines.wallet.manager import wallet_manager
        
        logger.info(
            f"Copy request [User: {req.user_id[:8]}]: {req.outcome} on {req.market_question[:40]}… "
            f"@ ${req.price:.3f} x ${req.size_usdc:.2f}"
        )

        # --- Safety checks ---
        capped_size = min(req.size_usdc, self.max_per_trade)
        if capped_size < req.size_usdc:
            logger.warning(
                f"Position capped from ${req.size_usdc} → ${capped_size} (max_per_trade)"
            )

        today = date.today().isoformat()
        spent_today = self._daily_spent.get(today, 0.0)
        remaining = self.max_daily - spent_today

        if remaining <= 0:
            return CopyTradeResult(
                status="error",
                message=f"Daily exposure limit reached (${self.max_daily:.0f}). Try tomorrow.",
            )

        if capped_size > remaining:
            capped_size = remaining
            logger.warning(f"Size further reduced to ${capped_size:.2f} (daily limit)")

        # Compute number of shares:  shares = usdc / price
        if req.price <= 0 or req.price >= 1:
            return CopyTradeResult(
                status="error",
                message=f"Invalid price {req.price}. Must be 0 < price < 1.",
            )

        shares = round(capped_size / req.price, 2)

        # --- Simulation mode ---
        if self.simulation:
            self._daily_spent[today] = spent_today + capped_size
            result = CopyTradeResult(
                status="simulated",
                message=(
                    f"[SIM] Would BUY {shares} shares of {req.outcome} "
                    f"@ ${req.price:.3f} = ${capped_size:.2f} exposure"
                ),
                trade={
                    "user_id": req.user_id,
                    "source_wallet": req.source_wallet,
                    "token_id": req.token_id,
                    "market_id": req.market_id,
                    "outcome": req.outcome,
                    "price": req.price,
                    "shares": shares,
                    "usdc": capped_size,
                    "simulation": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            self._log_trade(result)
            return result

        # --- Live execution ---
        try:
            # 1. Get User Proxy Wallet Key
            pk = wallet_manager.get_decrypted_key(req.user_id)
            if not pk:
                return CopyTradeResult(
                    status="error",
                    message="No proxy wallet found for your account. Please link or generate one."
                )

            # 2. Get dynamic authenticated client
            auth_client = await self.client.get_authenticated_client(pk)

            from py_clob_client.clob_types import OrderArgs, OrderType
            order_args = OrderArgs(
                token_id=req.token_id,
                price=req.price,
                size=shares,
                side="BUY",
            )
            signed = auth_client.create_order(order_args)
            response = auth_client.post_order(signed, orderType=OrderType.GTC)

            if response and response.get("success"):
                order_id = response.get("orderID", "")
                self._daily_spent[today] = spent_today + capped_size

                result = CopyTradeResult(
                    status="success",
                    order_id=order_id,
                    message=f"Order placed: {shares} × {req.outcome} @ ${req.price:.3f}",
                    trade={
                        "user_id": req.user_id,
                        "source_wallet": req.source_wallet,
                        "token_id": req.token_id,
                        "market_id": req.market_id,
                        "outcome": req.outcome,
                        "price": req.price,
                        "shares": shares,
                        "usdc": capped_size,
                        "order_id": order_id,
                        "simulation": False,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                self._log_trade(result)
                return result
            else:
                err = response.get("errorMsg", "Unknown") if response else "No response"
                return CopyTradeResult(status="error", message=f"Order rejected: {err}")

        except Exception as e:
            logger.error(f"Copy-trade execution error: {e}")
            return CopyTradeResult(status="error", message=str(e))

    def get_status(self) -> Dict[str, Any]:
        """Return current copy-executor status for API."""
        today = date.today().isoformat()
        spent = self._daily_spent.get(today, 0.0)
        return {
            "simulation": self.simulation,
            "max_per_trade": self.max_per_trade,
            "max_daily": self.max_daily,
            "spent_today": round(spent, 2),
            "remaining_today": round(max(0, self.max_daily - spent), 2),
        }

    def get_trade_log(self, limit: int = 20) -> list:
        """Fetch recent copy-trade log from Supabase."""
        if not self._supabase:
            return []
        try:
            resp = (
                self._supabase.table("copy_trades")
                .select("*")
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return resp.data or []
        except Exception as e:
            logger.error(f"Error fetching trade log: {e}")
            return []

    # ---- private -----------------------------------------------------------

    def _log_trade(self, result: CopyTradeResult):
        """Persist trade to Supabase (best-effort)."""
        if not self._supabase or not result.trade:
            return
        try:
            self._supabase.table("copy_trades").insert(result.trade).execute()
        except Exception as e:
            logger.debug(f"Could not log trade: {e}")
