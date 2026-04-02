"""
Telegram Notification Service (Personal Bot Mode)
--------------------------------------------------
Sends one-way push notifications to the admin chat.
No multi-user SaaS logic — this is a personal trading bot.

Events notified:
  - Bot start / stop
  - Trade executed
  - Trade rejected (high-value rejections only)
  - Trade resolved (WIN / LOSS)
  - Stop-loss triggered
  - Council budget warning (>90%)
  - Critical loop errors
"""

import html
import asyncio
from typing import Optional
from app.core.config import settings
from app.core.logging import logger


class TelegramNotifier:
    """
    Thin wrapper around the Telegram Bot API (via aiogram).
    Sends plain text messages to TELEGRAM_ADMIN_CHAT_ID.
    """

    def __init__(self):
        self._bot = None
        self._chat_id: Optional[str] = settings.TELEGRAM_ADMIN_CHAT_ID or None

        if settings.TELEGRAM_BOT_TOKEN and self._chat_id:
            try:
                from aiogram import Bot
                self._bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
                logger.info("TelegramNotifier: active (admin chat configured)")
            except ImportError:
                logger.warning("TelegramNotifier: aiogram not installed — notifications disabled")
        else:
            logger.info("TelegramNotifier: disabled (TELEGRAM_BOT_TOKEN or TELEGRAM_ADMIN_CHAT_ID not set)")

    # ── Public API ────────────────────────────────────────────────────────────

    async def notify(self, text: str) -> None:
        """
        Send a plain text message to the admin chat.
        Always call with await; silently swallows errors to never crash the bot.
        """
        if not self._bot or not self._chat_id:
            return
        try:
            await self._bot.send_message(
                chat_id=self._chat_id,
                text=text,
                parse_mode=None,   # plain text, no markdown risks
            )
        except Exception as e:
            logger.debug(f"TelegramNotifier: failed to send message: {e}")

    def notify_sync(self, text: str) -> None:
        """Fire-and-forget wrapper for non-async contexts."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.notify(text))
            else:
                loop.run_until_complete(self.notify(text))
        except Exception:
            pass

    # ── Pre-formatted event helpers ───────────────────────────────────────────

    async def bot_started(self, mode: str = "SIMULATION") -> None:
        emoji = "🟢" if mode != "REAL MONEY" else "🔴"
        await self.notify(f"{emoji} PolyMaster ONLINE\nMode: {mode}\nAutonomous trading active.")

    async def bot_stopped(self, reason: str = "Manual stop") -> None:
        await self.notify(f"🔴 PolyMaster OFFLINE\nReason: {reason}")

    async def trade_executed(self, market: str, outcome: str, score: float, size: float, sim: bool) -> None:
        tag = "[SIM]" if sim else "[LIVE]"
        market_short = market[:60] + ("..." if len(market) > 60 else "")
        await self.notify(
            f"🚀 TRADE EXECUTED {tag}\n"
            f"Market: {market_short}\n"
            f"Outcome: {outcome}  Score: {score:.2f}  Size: ${size:.0f}"
        )

    async def trade_resolved(self, market: str, result: str, pnl: Optional[float] = None) -> None:
        if result == "WIN":
            emoji = "✅ WIN"
            pnl_str = f"  (+${pnl:.2f})" if pnl is not None else ""
        else:
            emoji = "❌ LOSS"
            pnl_str = f"  (-${abs(pnl):.2f})" if pnl is not None else ""
        market_short = market[:60] + ("..." if len(market) > 60 else "")
        await self.notify(f"{emoji}{pnl_str}\n{market_short}")

    async def stop_loss_triggered(self, loss_pct: float) -> None:
        await self.notify(
            f"🛑 STOP-LOSS TRIGGERED\n"
            f"Daily loss exceeded {loss_pct:.0f}%. Bot pausing trades."
        )

    async def council_budget_warning(self, calls: int, budget: int) -> None:
        await self.notify(
            f"⚠️ Council budget: {calls}/{budget} calls today\n"
            f"Approaching daily limit — cache will handle remaining."
        )

    async def critical_error(self, error: str) -> None:
        short = str(error)[:200]
        await self.notify(f"🚨 CRITICAL ERROR\n{short}")


# Singleton — import this everywhere
telegram = TelegramNotifier()
