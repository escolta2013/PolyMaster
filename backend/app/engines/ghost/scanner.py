from loguru import logger
import httpx
from datetime import datetime
from app.core.client import PolyClient
from app.core.config import settings

class MarketScanner:
    """
    MarketScanner: Identifies high-volatility spikes (Hype) and 
    systematic probability decay (Nothing Ever Happens).
    Refactored for async performance and structured logging.
    """
    def __init__(self):
        self.client = PolyClient.get_instance()
        self.base_url = settings.GAMMA_API_URL
        self._price_cache = {} # token_id -> price

    async def scan_hype_spikes(self) -> list:
        """
        Scans for 'Hype Spikes' and 'Nothing Ever Happens' (NEH) opportunities.
        """
        logger.info("Starting Ghost Engine market scan...")
        async with httpx.AsyncClient() as client:
            try:
                params = {
                    "active": True,
                    "ascending": False,
                    "limit": 30
                }
                resp = await client.get(f"{self.base_url}/markets/keyset", params=params, timeout=10)
                resp.raise_for_status()
                res_data = resp.json()
                raw_markets = res_data.get("markets", [])
                
                results = []
                for m in raw_markets:
                    try:
                        question = m.get('question', 'Unknown Market')
                        market_id = m.get('conditionId', '0x')
                        clob_tokens = m.get('clobTokenIds')
                        if not clob_tokens: continue
                        
                        token_id_str = clob_tokens[0].strip('[]" ')
                        
                        # Fetch price via cache / SDK
                        price = await self.client.get_midpoint(token_id_str)
                        
                        prev_price = self._price_cache.get(token_id_str, price)
                        change = price - prev_price
                        self._price_cache[token_id_str] = price
                        
                        # Strategy Scoring logic
                        spike_mag = abs(change) * 15.0 + abs(price - 0.5) * 0.1
                        
                        grind_score = 0
                        if 0.6 < price < 0.9: grind_score += 0.4
                        vol_24h = float(m.get('volume24hr', 0))
                        if vol_24h < 150000: grind_score += 0.3
                        
                        liquidity_score = min(vol_24h / 10000, 95) + 5
                        
                        strategy = "Hype Scanner"
                        reason = "Momentum Shift"
                        
                        if change > 0.02:
                            reason = "Hype Spike 🚀"
                        elif grind_score > 0.6:
                            strategy = "No-Folio (NEH)"
                            reason = "Prob. Decay 📉"
                            spike_mag = grind_score
                        elif vol_24h > 1000000:
                            reason = "Deep Liquidity"

                        results.append({
                            "id": market_id,
                            "question": question,
                            "token_id": token_id_str,
                            "strategy": strategy,
                            "spike_magnitude": round(spike_mag, 3),
                            "liquidity_score": round(liquidity_score, 1),
                            "price": round(price, 3),
                            "reason": reason,
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        })
                    except Exception as e:
                        logger.debug(f"Error scanning market {m.get('id')}: {e}")
                        continue
                
                results.sort(key=lambda x: x['spike_magnitude'], reverse=True)
                logger.success(f"Ghost scan complete. Found {len(results)} opportunities.")
                return results

            except Exception as e:
                logger.error(f"Scanner Error: {e}")
                return []
