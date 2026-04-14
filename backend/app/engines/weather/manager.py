from loguru import logger
import httpx
import asyncio
import re
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from app.core.client import PolyClient
from app.core.config import settings
from app.engines.ghost.order_manager import OrderManager

class WeatherManager:
    """
    Weather Exploit Engine — Phase 4.4
    ==================================
    Exploits the latency between actual weather data (NOAA/HRRR) and 
    Polymarket sentiment. 
    
    Strategy: 
    1. Scan markets for city-based temperature/precipitation tasks.
    2. Fetch high-resolution real-time weather data for that city.
    3. If the actual value has already passed the threshold OR is 
       physically certain but market is mispriced (>15% discrepancy) -> Execute.
    """

    CITY_COORDS = {
        "NYC": {"lat": 40.71, "lon": -74.00},
        "New York": {"lat": 40.71, "lon": -74.00},
        "Dallas": {"lat": 32.77, "lon": -96.79},
        "Chicago": {"lat": 41.87, "lon": -87.62},
        "London": {"lat": 51.50, "lon": -0.12},
        "Seoul": {"lat": 37.56, "lon": 126.97},
        "Wellington": {"lat": -41.28, "lon": 174.77},
        "Paris": {"lat": 48.85, "lon": 2.35},
        "Miami": {"lat": 25.76, "lon": -80.19},
        "Phoenix": {"lat": 33.44, "lon": -112.07},
        "Los Angeles": {"lat": 34.05, "lon": -118.24},
        "Ankara": {"lat": 39.93, "lon": 32.85},
        "Istanbul": {"lat": 41.01, "lon": 28.97},
        "Madrid": {"lat": 40.41, "lon": -3.70},
        "Barcelona": {"lat": 41.38, "lon": 2.17},
        "Tokyo": {"lat": 35.67, "lon": 139.65},
        "Singapore": {"lat": 1.35, "lon": 103.82},
    }

    def __init__(self):
        self.client = PolyClient.get_instance()
        self.order_mgr = OrderManager()  # Authenticated order placement (same as Ghost engine)
        self.gamma_api = settings.GAMMA_API_URL
        self._last_scan = {} # market_id -> last_checked
        self.executed_markets = set() # Dedup guard against infinite executions

    async def scan_and_exploit(self):
        """Main entry point for the autonomous loop."""
        if not settings.ENABLE_WEATHER_EXP:
            return
            
        logger.info("Weather Exploit: Scanning for mispriced weather markets...")
        markets = await self._fetch_weather_markets()
        
        for market in markets:
            try:
                await self._process_market(market)
            except Exception as e:
                logger.error(f"Weather Exploit: Error processing {market.get('id')}: {e}")

    async def _fetch_weather_markets(self) -> List[Dict]:
        """Fetch active markets tagged with 'Weather' or having keywords."""
        async with httpx.AsyncClient() as http:
            # Polymarket use tags or search
            params = {
                "active": "true",
                "limit": 50,
                "order": "volume",
                "ascending": "false",
                # Hardcoded tags or keyword search in titles
            }
            url = f"{self.gamma_api}/markets/keyset"
            resp = await http.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                return []
                
            res_data = resp.json()
            all_m = res_data.get("markets", [])
            # Filter for keywords in question
            weather_keywords = ["temperature", "highest temperature", "rain", "precipitation", "snow"]
            return [
                m for m in all_m 
                if any(kw in m.get("question", "").lower() for kw in weather_keywords)
                and not m.get("closed")
            ]

    async def _process_market(self, market: Dict):
        """Analyzes a single market against real weather data."""
        question = market.get("question", "")
        market_id = market.get("id")
        
        # 1. Identify City and Coordinates
        city = self._extract_city(question)
        if not city:
            return
            
        coords = self.CITY_COORDS.get(city)
        if not coords:
            return

        # 2. Extract Threshold and Metric
        threshold = self._extract_threshold(question)
        if threshold is None: return
        
        # 3. Detect Unit
        unit = "fahrenheit"
        if "°c" in question.lower() or " celsius" in question.lower():
            unit = "celsius"
        elif "°f" in question.lower() or " fahrenheit" in question.lower():
            unit = "fahrenheit"
        # Default: US cities usually F, international usually C
        elif any(c in question for c in ["Seoul", "London", "Paris", "Ankara", "Istanbul", "Madrid", "Barcelona", "Tokyo", "Singapore", "Wellington"]):
            unit = "celsius"

        # 4. Fetch Live Weather Data (Open-Meteo)
        actual_temp = await self._get_live_weather(coords["lat"], coords["lon"], unit=unit)
        if actual_temp is None: return
        
        # 4. Compare with Market Price
        # We need the YES token
        token_ids = market.get("clobTokenIds", [])
        if isinstance(token_ids, str):
            try:
                import json
                token_ids = json.loads(token_ids)
            except:
                token_ids = []
        
        if not token_ids or not isinstance(token_ids, list): 
            logger.warning(f"Weather Exploit: No valid token IDs found for {market.get('id')}")
            return
            
        yes_token_id = token_ids[0]
        
        # Get market price
        intel = await self.client.get_orderbook(yes_token_id)
        current_price = intel.get("midpoint", 0.5)
        
        # Determine if "YES" means "Greater than" or "In range"
        # Most markets are "Highest temperature ... will be X or higher?"
        is_greater = "higher" in question.lower() or "above" in question.lower() or "or more" in question.lower()
        
        edge_found = False
        reason = ""
        
        if is_greater:
            # Case: Will it reach 62°F? 
            # If actual is ALREADY 63°F -> YES is 100% physically certain.
            if actual_temp >= (threshold + 0.2): # small buffer
                if current_price < 0.90: # Market is slow!
                    edge_found = True
                    reason = f"Actual temp ({actual_temp}) already above threshold ({threshold}). Market price {current_price} is lagging."
        else:
            # Case: Will it stay below 60°F? 
            # If actual is ALREADY 62°F -> NO is 100%. YES is 0%.
            if actual_temp > (threshold + 0.2):
                if current_price > 0.10: # YES is still priced high
                    edge_found = True
                    reason = f"Actual temp ({actual_temp}) already EXCEEDED threshold ({threshold}). YES should be 0, but is {current_price}."

        if edge_found:
            # 1. Check local memory (fast)
            if market_id in self.executed_markets:
                return 

            # 2. Check Supabase (persistent memory)
            try:
                from app.engines.wallet.manager import wallet_manager
                supabase = wallet_manager.supabase 
                
                # Check for ANY record for this market_id
                existing = supabase.table("autonomous_logs").select("id").eq("market_id", market_id).limit(1).execute()
                if existing.data:
                    logger.debug(f"Weather Exploit: Market {market_id} record found in DB. Skipping.")
                    self.executed_markets.add(market_id)
                    return
                
                # Add to local memory immediately to prevent race conditions within the same cycle
                self.executed_markets.add(market_id)
            except Exception as e:
                logger.error(f"Weather Exploit: DB dedup check failed: {e}")

            logger.success(f"Weather Exploit FOUND EDGE: {city} | {reason}")
            self.executed_markets.add(market_id)
            await self._execute_trade(market, yes_token_id, actual_temp, threshold, reason)

    def _extract_city(self, question: str) -> Optional[str]:
        for city in self.CITY_COORDS.keys():
            if city in question:
                return city
        return None

    def _extract_threshold(self, question: str) -> Optional[float]:
        # Regex for numbers followed by F or C
        match = re.search(r"(\d+)\s?(°|deg|degrees)?\s?([FC])", question, re.IGNORECASE)
        if match:
            return float(match.group(1))
        
        # Simple number search if metric isn't explicit but common sense
        match = re.search(r"(\d+\.?\d*)\s?(or higher|or more|or lower)", question, re.IGNORECASE)
        if match:
            return float(match.group(1))
            
        return None

    async def _get_live_weather(self, lat: float, lon: float, unit: str = "fahrenheit") -> Optional[float]:
        """Fetch current temperature from Open-Meteo (NOAA HRRR source for US)."""
        async with httpx.AsyncClient() as http:
            try:
                # Open-Meteo is free for non-commercial/low-volume
                url = "https://api.open-meteo.com/v1/forecast"
                params = {
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m",
                    "temperature_unit": unit,
                    "forecast_days": 1
                }
                resp = await http.get(url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                return data.get("current", {}).get("temperature_2m")
            except Exception as e:
                logger.error(f"Weather API Error: {type(e).__name__} - {str(e)}")
        return None

    async def _execute_trade(self, market: Dict, token_id: str, actual: float, threshold: float, reason: str):
        """Executes a trade based on the exploit."""
        from app.engines.ghost.order_manager import OrderManager
        from app.services.telegram_bot import telegram
        from app.engines.wallet.manager import wallet_manager
        order_mgr = OrderManager()
        
        mode = "SIMULATION" if settings.COPY_SIMULATION else "LIVE"
        
        # Determine side
        # If actual > threshold and it was "or higher", we buy YES.
        # If actual > threshold and it was "below", we buy NO (which in binary markets is buying the other token).
        # For simplicity, if edge_found was true, we buy the side that is undervalued.
        
        # If current_price < 0.90 but it's certain 100%, we buy at market/limit.
        side = "BUY"
        # In binary markets YES + NO = 1. 
        # If we need NO, we can buy the NO token. 
        # But our `_process_market` usually targets the YES price.
        # Default to YES token (first)
        target_token = ""
        token_ids = market.get("clobTokenIds", [])
        
        # Robust parsing for string vs list
        if isinstance(token_ids, str):
            try:
                import json
                token_ids = json.loads(token_ids)
            except:
                token_ids = []
                
        if not token_ids or not isinstance(token_ids, list):
            logger.error(f"Weather Exploit: Cannot execute trade, no valid token IDs for {market.get('id')}")
            return
            
        target_token = token_ids[0] # Default YES
        
        if "YES should be 0" in reason:
            # We want to buy NO. In Polymarket binary, it's usually the second token.
            if len(token_ids) > 1:
                target_token = token_ids[1] # NO token
            else:
                logger.warning("Weather Exploit: Needed NO token but only one found.")
                return

        size_usdc = settings.WEATHER_MAX_BUDGET
        logger.info(f"Weather Exploit [{mode}]: Placing trade on '{market.get('question')[:40]}...' | Reason: {reason}")
        
        if settings.COPY_SIMULATION:
            logger.success(f"Weather Exploit [SIM]: Would buy SHARES for {size_usdc} USDC on token {target_token}")
            await self._log_to_supabase(market, actual, threshold, reason, decision="EXECUTED_SIM", token_id=target_token)
        else:
            # Execution logic
            try:
                res = self.order_mgr.create_and_post_order(
                    token_id=target_token,
                    price=settings.WEATHER_PRICE_BUFFER, # Aggressive limit to take all lagging asks
                    size=size_usdc / settings.WEATHER_PRICE_BUFFER,
                    side="BUY"
                )
                if res.get("status") == "success":
                    order_id = res.get("order_id")
                    logger.success(f"Weather Exploit [LIVE]: Executed! Order ID: {order_id}")
                    # Notify Telegram with Balance
                    try:
                        balance = wallet_manager.get_onchain_balance(settings.POLY_PROXY_ADDRESS) if settings.POLY_PROXY_ADDRESS else 0.0
                        await telegram.trade_executed(
                            market=f"[WEATHER] {market.get('question')}",
                            outcome="YES",
                            score=1.0,
                            size=size_usdc,
                            sim=False,
                            balance=balance
                        )
                    except Exception as te:
                        logger.error(f"Weather Telegram notification failed: {te}")
                    await self._log_to_supabase(market, actual, threshold, reason, decision="EXECUTED_LIVE", token_id=target_token, order_id=order_id)
                else:
                    error_msg = res.get("message", "Unknown error")
                    logger.error(f"Weather Exploit [LIVE]: Execution failed: {error_msg}")
                    await self._log_to_supabase(market, actual, threshold, reason, decision="FAILED", token_id=target_token)
            except Exception as e:
                logger.error(f"Weather Exploit [LIVE]: Execution exception: {e}")
                await self._log_to_supabase(market, actual, threshold, reason, decision="ERROR", token_id=target_token)

    async def _log_to_supabase(self, market: Dict, actual: float, threshold: float, reason: str, decision: str, token_id: str, order_id: str = None):
        try:
            from supabase import create_client
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            supabase.table("autonomous_logs").insert({
                "market_id": market.get("id"),
                "market_question": f"[WEATHER] {market.get('question', '')[:200]}",
                "outcome": "YES/NO (Weather)",
                "council_score": 1.0, # Physical certainty
                "decision": decision,
                "token_id": token_id,
                "execution_tx": order_id, # Usamos el order_id como referencia
                "reasoning": {
                    "strategy": "Weather Exploit",
                    "actual_temp": actual,
                    "threshold": threshold,
                    "logic": reason
                },
                "size_usdc": settings.WEATHER_MAX_BUDGET,
                "detected_at": datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Weather Exploit: Failed to update Supabase log: {e}")

weather_manager = WeatherManager()
