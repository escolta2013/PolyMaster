import html
import asyncio
from typing import Optional, List, Dict
from app.core.config import settings
from app.core.logging import logger


class TelegramNotifier:
    """
    Thin wrapper around the Telegram Bot API (via aiogram/httpx).
    Sends one-way push notifications to the admin chat.
    """

    def __init__(self):
        self._token = settings.TELEGRAM_BOT_TOKEN
        self._chat_id = settings.TELEGRAM_ADMIN_CHAT_ID

        if self._token and self._chat_id:
            logger.info("TelegramNotifier: active (admin chat configured)")
        else:
            logger.info("TelegramNotifier: disabled (TELEGRAM_BOT_TOKEN or TELEGRAM_ADMIN_CHAT_ID not set)")

    # ── Public API ────────────────────────────────────────────────────────────

    async def notify(self, text: str) -> None:
        """
        Send a plain text message to the admin chat using HTTPX directly.
        Always call with await; silently swallows errors to never crash the bot.
        """
        if not self._token or not self._chat_id:
            return
            
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, timeout=10.0)
                if resp.status_code != 200:
                    data = resp.json()
                    logger.warning(f"TelegramNotifier failed: {data.get('description', 'Unknown Error')}")
        except Exception as e:
            logger.warning(f"TelegramNotifier request failed: {e}")

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
        emoji = "🟢"
        mode_str = f"🧪 {mode}" if mode == "SIMULATION" else f"⚡ {mode}"
        await self.notify(f"{emoji} PolyMaster ONLINE\nMode: {mode_str}\nAutonomous trading active.")

    async def bot_stopped(self, reason: str = "Manual stop") -> None:
        await self.notify(f"🔴 PolyMaster OFFLINE\nReason: {reason}")

    async def trade_executed(self, market: str, outcome: str, score: float, size: float, sim: bool, balance: float = 0.0) -> None:
        tag = "🧪 [SIMULACIÓN]" if sim else "⚡ [LIVE TRADE]"
        market_short = market[:60] + ("..." if len(market) > 60 else "")
        msg = (
            f"<b>{tag}</b>\n"
            f"🎯 <b>Mercado:</b> {market_short}\n"
            f"✅ <b>Posición:</b> {outcome}\n"
            f"📊 <b>Score AI:</b> {score:.2f}\n"
            f"💰 <b>Tamaño:</b> ${size:,.2f} USDC\n"
            f"🏦 <b>Balance actual:</b> ${balance:,.2f} USDC"
        )
        await self.notify(msg)

    async def trade_failed(self, market: str, outcome: str, error: str) -> None:
        market_short = market[:60] + ("..." if len(market) > 60 else "")
        msg = (
            f"❌ <b>FALLO EN EJECUCIÓN</b>\n"
            f"🎯 <b>Mercado:</b> {market_short}\n"
            f"✅ <b>Intento:</b> {outcome}\n"
            f"⚠️ <b>Error:</b> {error}"
        )
        await self.notify(msg)

    async def notify_status(self, balance: float, trades_24h: int, profit_24h: float, failures_24h: int = 0) -> None:
        """Periodic status update."""
        mode_tag = "🧪 SIMULACIÓN" if settings.COPY_SIMULATION else "⚡ LIVE"
        msg = (
            f"📊 <b>ESTADO DEL BOT ({mode_tag})</b>\n"
            f"──────────────\n"
            f"🏦 <b>Balance Wallet:</b> ${balance:,.2f} USDC\n"
            f"🔄 <b>Trades (24h):</b> {trades_24h}\n"
            f"🔴 <b>Fallos (24h):</b> {failures_24h}\n"
            f"📈 <b>P&L (24h):</b> {profit_24h:+.2f} USDC\n"
            f"──────────────\n"
            f"Status: Corriendo ✅"
        )
        await self.notify(msg)

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
