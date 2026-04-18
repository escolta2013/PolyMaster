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
        "NYC": {"lat": 40.71, "lon": -74.00, "is_us": True},
        "New York": {"lat": 40.71, "lon": -74.00, "is_us": True},
        "Dallas": {"lat": 32.77, "lon": -96.79, "is_us": True},
        "Chicago": {"lat": 41.87, "lon": -87.62, "is_us": True},
        "London": {"lat": 51.50, "lon": -0.12, "is_us": False},
        "Seoul": {"lat": 37.56, "lon": 126.97, "is_us": False},
        "Wellington": {"lat": -41.28, "lon": 174.77, "is_us": False},
        "Paris": {"lat": 48.85, "lon": 2.35, "is_us": False},
        "Miami": {"lat": 25.76, "lon": -80.19, "is_us": True},
        "Phoenix": {"lat": 33.44, "lon": -112.07, "is_us": True},
        "Los Angeles": {"lat": 34.05, "lon": -118.24, "is_us": True},
        "Ankara": {"lat": 39.93, "lon": 32.85, "is_us": False},
        "Istanbul": {"lat": 41.01, "lon": 28.97, "is_us": False},
        "Madrid": {"lat": 40.41, "lon": -3.70, "is_us": False},
        "Barcelona": {"lat": 41.38, "lon": 2.17, "is_us": False},
        "Tokyo": {"lat": 35.67, "lon": 139.65, "is_us": False},
        "Singapore": {"lat": 1.35, "lon": 103.82, "is_us": False},
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
                "active": True,
                "limit": settings.WEATHER_SCAN_LIMIT,
                "order": "volume",
                "ascending": False,
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

        # 4. Fetch Live Weather Data Consensus
        actual_temps = await self._get_live_weather_consensus(coords, unit)
        if not actual_temps or len(actual_temps) < 2:
            logger.debug(f"Weather Exploit [Consensus Failed]: Only {len(actual_temps) if actual_temps else 0} APIs returned valid data for {city}.")
            return
            
        # Determine strict consensus actual_temp for logging
        actual_temp = round(sum(actual_temps) / len(actual_temps), 2)
        
        # 5. Compare with Market Price
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
            # ALL apis must report that actual temp is >= threshold
            if all(t >= (threshold + 0.2) for t in actual_temps):
                if current_price < settings.WEATHER_ENTRY_THRESHOLD_HIGH: # Market is slow!
                    edge_found = True
                    reason = f"Consensus temps {actual_temps} ALL above threshold ({threshold}). Market price {current_price} is lagging."
        else:
            # Case: Will it stay below 60°F? 
            # ALL apis must report that actual temp > threshold
            if all(t > (threshold + 0.2) for t in actual_temps):
                if current_price > settings.WEATHER_ENTRY_THRESHOLD_LOW: # YES is still priced high
                    edge_found = True
                    reason = f"Consensus temps {actual_temps} ALL EXCEEDED threshold ({threshold}). YES should be 0, but is {current_price}."

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
                
                # Minimum Budget Check
                min_size = getattr(settings, "MIN_ORDER_SIZE_USD", 5.0)
                if settings.WEATHER_MAX_BUDGET < min_size:
                    logger.warning(f"Weather Exploit: Budget ({settings.WEATHER_MAX_BUDGET}) is below minimum required ({min_size}). Skipping.")
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

    async def _get_live_weather_consensus(self, coords: Dict[str, Any], unit: str) -> Optional[List[float]]:
        lat, lon = coords["lat"], coords["lon"]
        is_us = coords.get("is_us", False)
        
        async with httpx.AsyncClient() as http:
            tasks = [
                self._fetch_openmeteo(lat, lon, unit, http),
                self._fetch_weatherapi(lat, lon, unit, http)
            ]
            if is_us:
                tasks.append(self._fetch_noaa(lat, lon, unit, http))
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            valid_temps = [r for r in results if isinstance(r, (int, float))]
            return valid_temps

    async def _fetch_openmeteo(self, lat: float, lon: float, unit: str, http: httpx.AsyncClient) -> Optional[float]:
        try:
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
            return resp.json().get("current", {}).get("temperature_2m")
        except Exception as e:
            logger.error(f"Open-Meteo Error: {e}")
        return None

    async def _fetch_noaa(self, lat: float, lon: float, unit: str, http: httpx.AsyncClient) -> Optional[float]:
        """Fetch current temperature from NOAA API (US ONLY)."""
        try:
            headers = {"User-Agent": "(PolyMasterTradingBot, admin@polymaster.com)"}
            pts_url = f"https://api.weather.gov/points/{lat},{lon}"
            pts_resp = await http.get(pts_url, headers=headers, timeout=10)
            pts_resp.raise_for_status()
            forecast_url = pts_resp.json().get("properties", {}).get("forecastHourly")
            if not forecast_url: return None
            
            f_resp = await http.get(forecast_url, headers=headers, timeout=10)
            f_resp.raise_for_status()
            periods = f_resp.json().get("properties", {}).get("periods", [])
            if periods:
                temp_f = periods[0].get("temperature")
                if unit == "celsius":
                    return round((temp_f - 32) * 5.0 / 9.0, 1)
                return temp_f
        except httpx.HTTPStatusError as e:
            logger.error(f"NOAA API Status Error ({e.response.status_code}) for {e.request.url}")
        except httpx.TimeoutException:
            logger.error("NOAA API Timeout: El servidor de NOAA no respondió a tiempo.")
        except Exception as e:
            logger.error(f"NOAA API Unexpected Error: {type(e).__name__} - {e}")
        return None

    async def _fetch_weatherapi(self, lat: float, lon: float, unit: str, http: httpx.AsyncClient) -> Optional[float]:
        key = getattr(settings, "WEATHER_API_KEY", None)
        if not key: return None
        try:
            url = f"http://api.weatherapi.com/v1/current.json?key={key}&q={lat},{lon}"
            resp = await http.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if unit == "fahrenheit":
                return data.get("current", {}).get("temp_f")
            else:
                return data.get("current", {}).get("temp_c")
        except Exception as e:
            logger.error(f"WeatherAPI Error: {e}")
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
            
        exec_outcome = "YES" # Default
        if "YES should be 0" in reason:
            exec_outcome = "NO"
            # We want to buy NO. In Polymarket binary, it's usually the second token.
            if len(token_ids) > 1:
                target_token = token_ids[1] # NO token
            else:
                logger.warning("Weather Exploit: Needed NO token but only one found.")
                return

        # Testing mode sizing: Use $5.50 (Polymarket minimum is ~$5.00)
        # to allow multiple trades with small balance.
        try:
            balance = wallet_manager.get_onchain_balance(settings.POLY_PROXY_ADDRESS) if settings.POLY_PROXY_ADDRESS else 0.0
            
            # Use $5.50 as the preferred test size
            test_size = 5.50
            
            # Cap it by balance just in case, but warn if below minimum
            size_usdc = min(test_size, float(balance) * 0.95)
            
            if size_usdc < 5.0:
                logger.warning(f"Weather Exploit [TEST MODE]: Balance too low for minimum $5 trade (Have: ${size_usdc:.2f}). Skipping.")
                return
        except Exception as b_e:
            logger.warning(f"Weather Exploit: Could not fetch live balance, using fallback test size: {b_e}")
            size_usdc = 5.50

        logger.info(f"Weather Exploit [{mode}]: TEST MODE - Placing trade of ${size_usdc:.2f} | Reason: {reason}")
        
        if settings.COPY_SIMULATION:
            logger.success(f"Weather Exploit [SIM]: Would buy SHARES for {size_usdc} USDC on token {target_token}")
            await self._log_to_supabase(market, actual, threshold, reason, decision="EXECUTED_SIM", token_id=target_token, size_usdc=size_usdc, outcome=exec_outcome)
            # Log to copy_trades for dashboard stats
            await self._log_copy_trade_record(market, target_token, exec_outcome, size_usdc, "SIM_EXEC")
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
                    await self._log_to_supabase(market, actual, threshold, reason, decision="EXECUTED_LIVE", token_id=target_token, size_usdc=size_usdc, order_id=order_id, outcome=exec_outcome)
                    await self._log_copy_trade_record(market, target_token, exec_outcome, size_usdc, order_id)
                else:
                    error_msg = res.get("message", "Unknown error")
                    logger.error(f"Weather Exploit [LIVE]: Execution failed: {error_msg}")
                    await self._log_to_supabase(market, actual, threshold, reason, decision="FAILED", token_id=target_token, size_usdc=size_usdc)
            except Exception as e:
                logger.error(f"Weather Exploit [LIVE]: Execution exception: {e}")
                await self._log_to_supabase(market, actual, threshold, reason, decision="ERROR", token_id=target_token, size_usdc=size_usdc, outcome=exec_outcome)

    async def _log_to_supabase(self, market: Dict, actual: float, threshold: float, reason: str, decision: str, token_id: str, size_usdc: float, outcome: str, order_id: str = None):
        try:
            from supabase import create_client
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            supabase.table("autonomous_logs").insert({
                "market_id": market.get("id"),
                "market_question": f"[WEATHER] {market.get('question', '')[:200]}",
                "outcome": outcome,
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
                "size_usdc": size_usdc,
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "end_date_iso": market.get("end_date_iso")
            }).execute()
        except Exception as e:
            logger.error(f"Weather Exploit: Failed to update Supabase log: {e}")

    async def _log_copy_trade_record(self, market: Dict, token_id: str, outcome: str, size_usdc: float, order_id: str):
        """Helper to log weather trades to copy_trades table for dashboard syncing."""
        try:
            from supabase import create_client
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            
            # Polymarket price at entry for weather engine is usually high (lagging)
            # or low if we buy early. We don't have perfect price history here, 
            # so we estimate it but the dashboard uses it for ROI.
            # Best is to use a nominal price like 0.90 for successes.
            estimated_price = 0.90
            shares = size_usdc / estimated_price
            
            trade_record = {
                "user_id": "WEATHER_ENGINE",
                "source_wallet": "Consensus",
                "token_id": token_id,
                "market_id": market.get("id"),
                "outcome": outcome,
                "price": estimated_price,
                "shares": round(shares, 2),
                "usdc": size_usdc,
                "order_id": order_id,
                "simulation": settings.COPY_SIMULATION,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            supabase.table("copy_trades").insert(trade_record).execute()
        except Exception as e:
            logger.error(f"Weather Exploit: Failed to log to copy_trades: {e}")

weather_manager = WeatherManager()
