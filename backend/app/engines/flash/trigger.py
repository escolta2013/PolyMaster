from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger
from app.engines.tracker import indexer
from app.engines.flash.sniper import FlashEngine
import asyncio

@dataclass
class SpikeAlert:
    market_id: str
    token_id: str
    outcome: str
    price_before: float
    price_now: float
    change_pct: float
    timestamp: datetime

class SpikeTrigger:
    """
    Monitors market data for sudden price movements (Spikes).
    Triggers Flash Engine execution if the spike exceeds threshold.
    """
    
    def __init__(self, threshold_pct: float = 0.10, window_sec: int = 1):
        self.threshold = threshold_pct
        self.window = timedelta(seconds=window_sec)
        # Replaced in-memory history with Redis
        import redis
        self.redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.history_key = "flash:price_history"
        
        self.flash = FlashEngine()
        self.running = False

    async def monitor_stream(self):
        """
        Emulated tick stream monitor. In production, this would subscribe to CLOB WebSocket.
        """
        logger.info("⚡ Spike Trigger Active: Monitoring for >10% moves...")
        self.running = True
        
        while self.running:
            try:
                # Fetch hot markets
                markets = await indexer.fetch_active_markets(limit=20)
                
                for m in markets:
                    for token in m.get("tokens", []):
                        t_id = token.get("token_id")
                        price = float(token.get("price", 0))
                        
                        await self._process_tick(m["id"], t_id, token["outcome"], price)
                
                await asyncio.sleep(0.5) # Sub-second polling
            except Exception as e:
                # logger.error(f"Spike Monitor Error: {e}")
                await asyncio.sleep(1)

    async def _process_tick(self, market_id: str, token_id: str, outcome: str, price: float):
        now = datetime.utcnow()
        now_ts = now.timestamp()
        
        # Get last price from Redis
        if price <= 0: return

        try:
            last_data_raw = self.redis.hget(self.history_key, token_id)
            if last_data_raw:
                last_data = eval(last_data_raw) # simple dict eval
                last_price = float(last_data["p"])
                last_ts = float(last_data["t"])
                
                # Check if within window
                if (now_ts - last_ts) <= self.window.total_seconds():
                    change = (price - last_price) / last_price
                    
                    if abs(change) >= self.threshold:
                        logger.warning(f"🚨 SPIKE DETECTED: {outcome} moved {change*100:.1f}% in {(now_ts-last_ts):.2f}s")
                        
                        alert = SpikeAlert(
                            market_id=market_id,
                            token_id=token_id,
                            outcome=outcome,
                            price_before=last_price,
                            price_now=price,
                            change_pct=change,
                            timestamp=now
                        )
                        # Trigger Flash Execution logic
                        # await self.flash.snipe_transaction(...)

            # Update Redis
            self.redis.hset(self.history_key, token_id, str({"p": price, "t": now_ts}))
            
        except Exception as e:
            logger.error(f"Redis Error: {e}")

spike_monitor = SpikeTrigger()
