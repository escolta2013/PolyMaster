import aiohttp
from loguru import logger
from typing import Optional, Dict

class CryptoFeed:
    """
    Fetches real-time crypto prices from Binance (Public API).
    Used for Lag Arbitrage against Polymarket odds.
    """
    
    BASE_URL = "https://api.binance.com/api/v3"

    @staticmethod
    async def get_price(symbol: str) -> Optional[float]:
        """
        Get current price for a symbol (e.g. 'BTC', 'ETH', 'SOL').
        """
        # Map common symbols to Binance pairs
        symbol_map = {
            "BTC": "BTCUSDT",
            "ETH": "ETHUSDT",
            "SOL": "SOLUSDT",
            "DOGE": "DOGEUSDT",
            "BNB": "BNBUSDT"
        }
        
        pair = symbol_map.get(symbol.upper())
        if not pair:
            return None

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{CryptoFeed.BASE_URL}/ticker/price?symbol={pair}"
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = float(data["price"])
                        # logger.info(f"CryptoFeed: {symbol} Price = ${price:,.2f}")
                        return price
                    else:
                        logger.warning(f"CryptoFeed: Binance returned {response.status} for {symbol}")
                        return None
        except Exception as e:
            logger.error(f"CryptoFeed Error: {e}")
            return None
