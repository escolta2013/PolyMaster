from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.core.config import settings
from app.core.logging import logger
import asyncio

class TelegramService:
    """
    Service to manage the Telegram Bot and Signal publishing.
    """
    def __init__(self):
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN) if settings.TELEGRAM_BOT_TOKEN else None
        self.dp = Dispatcher()
        self._setup_handlers()

    def _setup_handlers(self):
        @self.dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            await message.answer(
                "🛡️ **PolyMaster Signal Gateway**\n\n"
                "Welcome to the institutional trading bridge. I'll pass you real-time signals from the Tracker Engine.\n\n"
                "Use /status to check your connected proxy wallet.",
                parse_mode="Markdown"
            )

        @self.dp.message(Command("status"))
        async def cmd_status(message: types.Message):
            # In a real scenario, we'd map Telegram ID to User ID
            await message.answer("🔍 Fetching your account status...")

        @self.dp.callback_query(lambda c: c.data and c.data.startswith("copy_"))
        async def process_copy_trade(callback_query: types.CallbackQuery):
            # Format: copy_{market_id}_{token_id}_{outcome}_{price}
            _, m_id, t_id, outcome, price = callback_query.data.split("_")
            
            await callback_query.message.edit_text(f"⏳ Executing Copy Trade for {outcome}...")
            
            # TODO: Pull real userId mapped to telegram ID
            from app.engines.tracker.copy_executor import CopyExecutor, CopyTradeRequest
            executor = CopyExecutor()
            
            req = CopyTradeRequest(
                user_id="default-user-id", # Placeholder
                source_wallet="Telegram-Signal",
                token_id=t_id,
                market_id=m_id,
                market_question="Market from Telegram",
                outcome=outcome,
                price=float(price),
                size_usdc=settings.MIN_ORDER_SIZE_USD / 5 # Arbitrary small size for 1-tap
            )
            
            try:
                result = await executor.execute_copy(req)
                if result.status in ["success", "simulated"]:
                    icon = "✅" if result.status == "success" else "🧪"
                    await callback_query.message.edit_text(
                        f"{icon} **Execution {result.status.upper()}**\n\n"
                        f"Target: {outcome} @ ${price}\n"
                        f"Status: {result.message}\n"
                        f"TX Hash: `{result.order_id or 'N/A'}`",
                        parse_mode="Markdown"
                    )
                else:
                    await callback_query.message.edit_text(f"❌ Execution Failed: {result.message}")
            except Exception as e:
                await callback_query.message.edit_text(f"❌ System Error: {str(e)}")

    async def send_signal(self, chat_id: str, title: str, description: str, market_id: str, token_id: str, outcome: str, price: float):
        """
        Published a trade signal to a specific user with execution buttons.
        """
        if not self.bot:
            logger.warning("Telegram Bot Token not set. Signal suppressed.")
            return

        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(
            text=f"🚀 Copy {outcome} @ ${price}",
            callback_data=f"copy_{market_id}_{token_id}_{outcome}_{price}")
        )
        builder.row(types.InlineKeyboardButton(
            text="📊 View Market",
            url=f"https://polymarket.com/event/{market_id}")
        )

        message_text = (
            f"🎯 **NEW SMART MONEY SIGNAL**\n\n"
            f"**Market:** {title}\n"
            f"**Action:** {description}\n\n"
            f"**Recommendation:** BUY {outcome} at < ${price}\n"
            f"**Confidence:** High (Grade A Clusters Detected)"
        )

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message_text,
                parse_mode="Markdown",
                reply_markup=builder.as_markup()
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram signal: {e}")

    async def start(self):
        if self.bot:
            logger.info("Starting Telegram Bot Polling...")
            await self.dp.start_polling(self.bot)

telegram_service = TelegramService()
