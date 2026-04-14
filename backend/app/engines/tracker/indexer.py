from loguru import logger
import httpx
from typing import List, Dict, Any, Set
from datetime import datetime, timezone, timedelta
from app.core.client import PolyClient
from app.core.config import settings

class PolymarketIndexer:
    """
    Fetches market data from Polymarket using async httpx and centralized settings.
    """
    
    def __init__(self):
        self.clob_client = PolyClient.get_instance()
        self.base_url = settings.GAMMA_API_URL

    async def get_top_markets(self, limit: int = 20, min_vol: int = 0) -> List[Dict[str, Any]]:
        """
        Fetch top markets by volume asynchronously.
        """
        async with httpx.AsyncClient() as client:
            try:
                # PHASE 1: Gamma Fetch
                # - Paper Mode:  Order by VOLUME to get the most liquid markets for calibration
                #                (freshness doesn't matter; we want real price discovery)
                # - Production:  Order by createdAt to find fresh opportunities before the market forms
                is_paper = settings.PAPER_TRADING_MODE
                all_markets = []
                cursor = None
                url = f"{self.base_url}/markets/keyset"
                
                # keyset pagination loop to fetch up to 500 markets safely
                target_total = 500
                while len(all_markets) < target_total:
                    params = {
                        "limit": 100,
                        "ascending": False,
                        "active": True
                    }
                    if cursor:
                        params["after_cursor"] = cursor
                        
                    response = await client.get(url, params=params, timeout=20.0)
                    if response.status_code != 200:
                        logger.warning(f"Indexer: Keyset API error {response.status_code}")
                        break
                        
                    res_data = response.json()
                    page = res_data.get("markets", [])
                    if not page:
                        break
                        
                    all_markets.extend(page)
                    cursor = res_data.get("next_cursor")
                    if not cursor:
                        break
                
                data = all_markets

                
                valid = []
                now_utc = datetime.now(timezone.utc)
                is_paper = settings.COPY_SIMULATION
                
                # Coarse filter thresholds — Relaxed for Production debugging
                age_limit = None
                min_volume = 100

                
                for m in data:
                    # LOCAL FILTERING: Robust type handling (sometimes Gamma returns strings)
                    closed = str(m.get("closed", "")).lower() == "true"
                    archived = str(m.get("archived", "")).lower() == "true"
                    active = str(m.get("active", "")).lower() == "true"
                    
                    if closed or archived or not active:
                        continue
                    
                    # Layer 1: Age filter (SKIPPED entirely in Paper Mode)
                    if age_limit is not None:
                        try:
                            ca_str = m.get("createdAt") or m.get("creationDate")
                            if ca_str:
                                created_at = datetime.fromisoformat(ca_str.replace("Z", "+00:00"))
                                if now_utc - created_at > age_limit:
                                    continue
                        except:
                            pass # If we can't parse date, treat as valid for safety
                    
                    # Layer 2: Volume > threshold (Coarse traction filter)
                    vol = float(m.get("volume", 0) or 0)
                    if vol < min_volume:
                        continue
                        
                    valid.append(m)
                
                # PHASE 2: CLOB Spot-Check (Fine Filter)
                # We check the top performers from our filtered list
                check_count = 300 if is_paper else 150
                candidates_to_check = valid[:check_count]
                import asyncio
                
                # Use Semaphore to avoid overwhelming the API and getting 502s
                sem = asyncio.Semaphore(30)
                
                async def verify_market_quality(market):
                    async with sem:
                        try:
                            token_ids_raw = market.get("clobTokenIds") or "[]"
                            if isinstance(token_ids_raw, str):
                                import json
                                tids = json.loads(token_ids_raw)
                            else:
                                tids = token_ids_raw
                            
                            if not tids: return None

                            # Use Gamma price data if available as a reliable fallback/source
                            g_bid = market.get("bestBid")
                            g_ask = market.get("bestAsk")
                            g_spread = market.get("spread")
                            
                            q = market.get("question", "Unknown") # Define q here for logging
                            
                            if g_bid is not None and g_ask is not None:
                                best_bid = float(g_bid)
                                best_ask = float(g_ask)
                                spread = float(g_spread) if g_spread is not None else (best_ask - best_bid)
                                midpoint = (best_ask + best_bid) / 2
                                logger.debug(f"Indexer: Using Gamma price data for '{q[:30]}': B:{best_bid} A:{best_ask} S:{spread}")
                                # For Gamma-sourced prices, we don't have an 'ob' object directly for depth.
                                # We'll need to fetch it or default it. For now, let's fetch it if we need depth.
                                ob = await self.clob_client.get_orderbook(tids[0]) # Still need CLOB for depth
                            else:
                                # Fallback to CLOB Spot-Check
                                ob = await self.clob_client.get_orderbook(tids[0])
                                best_ask = float(ob.get("best_ask") or 1.0)
                                best_bid = float(ob.get("best_bid") or 0.0)
                                midpoint = float(ob.get("midpoint", 0.5))
                                spread = best_ask - best_bid
                                logger.debug(f"Indexer: Using CLOB price data for '{q[:30]}': B:{best_bid} A:{best_ask} S:{spread}")

                            # Depth calculation (Top levels)
                            ask_depth = float(ob.get("ask_depth", 0))
                            bid_depth = float(ob.get("bid_depth", 0))

                            # VPIN components: total size on each side of the book
                            # VPIN = |bid_depth - ask_depth| / (bid_depth + ask_depth)
                            # Passed to Director as clob_bids_size / clob_asks_size
                            # Director uses these to detect informed flow (VPIN > 0.6 = kill switch)
                            
                            # Update market object
                            market["clob_verified_price"] = midpoint
                            market["clob_best_ask"] = best_ask
                            market["clob_best_bid"] = best_bid
                            market["clob_spread"] = spread
                            market["clob_ask_depth"] = ask_depth
                            market["clob_bids_size"] = bid_depth   # VPIN: buy-side pressure
                            market["clob_asks_size"] = ask_depth   # VPIN: sell-side pressure
                            
                            return market
                        except Exception:
                            return None

                spot_tasks = [verify_market_quality(m) for m in candidates_to_check]
                verified_results = await asyncio.gather(*spot_tasks)
                
                # APPLY QUALITY FILTERS
                final_candidates = []
                stats = {"price_fail": 0, "spread_fail": 0, "depth_fail": 0}
                
                # Paper Mode: Relax filters to get more calibration data
                min_p = 0.15 
                max_p = 0.85
                max_spread = settings.PAPER_TRADING_MAX_SPREAD if settings.PAPER_TRADING_MODE else 0.15

                
                for m in verified_results:
                    if m is None: 
                        # This happens if a market has no CLOB token or orderbook fails
                        continue
                    
                    p = m.get("clob_verified_price", 0.5)
                    s = m.get("clob_spread", 1.0)
                    d = m.get("clob_ask_depth", 0)
                    q = m.get("question", "Unknown")
                    
                    # Layer 1: Price (Relaxed for Paper)
                    if p < min_p or p > max_p:
                        stats["price_fail"] += 1
                        logger.info(f"Indexer Reject [P]: '{q[:30]}' (Price {p:.3f} outside {min_p}-{max_p})")
                        continue
                        
                    # Layer 2: Spread
                    if s > max_spread:
                        stats["spread_fail"] += 1
                        logger.info(f"Indexer Reject [S]: '{q[:30]}' (Spread {s:.3f} > {max_spread})")
                        continue
                        
                    # Layer 3: Depth (Skip/Relax for Paper)
                    min_depth = 0.0 if is_paper else 10.0
                    if d < min_depth:
                        stats["depth_fail"] += 1
                        logger.info(f"Indexer Reject [D]: '{q[:30]}' (Depth {d:.1f} < {min_depth})")
                        continue
                    
                    # Layer 4: Exclude NBA, Tennis and unpredictable categories
                    _q_lower = q.lower()
                    _nba_kw = ["nba", " vs ", " vs. ", "76ers", "celtics", "lakers",
                        "warriors", "knicks", "nets", "bucks", "heat", "nuggets", "suns",
                        "clippers", "grizzlies", "thunder", "mavs", "mavericks", "spurs",
                        "rockets", "pistons", "pacers", "hawks", "hornets", "wizards",
                        "magic", "raptors", "cavaliers", "timberwolves", "pelicans",
                        "kings", "blazers", "okc", "bulls", "basketball", "total points"]
                    _tennis_kw = ["tennis", " atp ", "wta ", "wimbledon", "roland garros",
                        "us open", "australian open", "djokovic", "alcaraz", "sinner"]
                    _excluded_kw = _nba_kw + _tennis_kw
                    if any(k in _q_lower for k in _excluded_kw):
                        logger.info(f"Indexer Reject [CAT]: '{q[:40]}' (excluded category)")
                        continue
                    logger.success(f"Indexer Match: '{q[:40]}' | P={p:.3f} | S={s:.3f} | D={d:.1f}")
                    final_candidates.append(m)


                # SMART SORTING: Highest REAL uncertainty (closest to 0.5)
                final_candidates.sort(key=lambda x: abs(0.5 - x["clob_verified_price"]))
                
                # Apply limit
                final_selection = final_candidates[:limit]
                
                spread_label = f"Spread < {max_spread}" if settings.PAPER_TRADING_MODE else "Spread < 0.15"
                mode_label = " [PAPER]" if settings.PAPER_TRADING_MODE else ""
                coarse_label = f"No age limit, Vol>${min_volume/1000:.0f}k" if settings.PAPER_TRADING_MODE else "Age<72h, Vol>$3k"
                price_label = f"Price {min_p}-{max_p}"
                logger.info(
                    f"Indexer (Hybrid){mode_label}: {len(data)} Fetched -> {len(valid)} Coarse ({coarse_label}) -> "
                    f"{len(final_selection)} Actionable ({price_label}, {spread_label}, Depth > {min_depth if 'min_depth' in locals() else 10.0}). "
                    f"Fails: {stats['price_fail']}P, {stats['spread_fail']}S, {stats['depth_fail']}D"
                )
                return final_selection
            except Exception as e:
                logger.error(f"Error fetching top markets: {e}")
                return []

    async def get_reward_markets(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find markets that offer liquidity rewards.
        """
        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.base_url}/markets/keyset"
                params = {
                    "limit": limit,
                    "active": True
                }
                response = await client.get(url, params=params, timeout=10)
                all_raw = response.json()
                all_markets = all_raw.get("markets", [])
                
                # Filter markets with rewards > 0
                r_markets = [
                    m for m in all_markets 
                    if m.get("rewards") and len(m.get("rewards")) > 0
                ]
                return r_markets
            except Exception as e:
                logger.error(f"Error fetching reward markets: {e}")
                return []

    async def get_market_details(self, market_id: str) -> Dict[str, Any]:
        """
        Fetch details for a specific market asynchronously.
        """
        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.base_url}/markets/{market_id}"
                response = await client.get(url, timeout=10)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Error fetching market details for {market_id}: {e}")
                return {}

    async def discover_active_wallets(self, seed_addresses: List[str] = None) -> Set[str]:
        """
        Stage 1 – Seed scan: Check positions of known whale addresses.
        """
        discovered = set()
        seeds = seed_addresses or []

        for address in seeds:
            try:
                positions = await self.clob_client.get_user_positions(address)
                if positions:
                    discovered.add(address)
                    logger.info(f"Seed wallet active: {address[:10]}... ({len(positions)} positions)")
            except Exception as e:
                logger.debug(f"Error checking seed {address[:10]}...: {e}")

        return discovered

    async def snowball_discover(self, known_wallets: Set[str], max_markets: int = 5) -> Set[str]:
        """
        Stage 2: Snowball — find wallets that trade alongside known whales.
        """
        new_wallets: Set[str] = set()
        data_api = settings.DATA_API_URL

        async with httpx.AsyncClient() as client:
            for addr in list(known_wallets)[:10]:
                try:
                    positions = await self.clob_client.get_user_positions(addr)
                    if not positions:
                        continue

                    # Pick top N markets by position size
                    sorted_pos = sorted(
                        positions,
                        key=lambda p: abs(float(p.get("size", 0))),
                        reverse=True,
                    )

                    for pos in sorted_pos[:max_markets]:
                        asset_id = pos.get("asset", "")
                        if not asset_id:
                            continue

                        # Fetch trades in that market asynchronously
                        try:
                            url = f"{data_api}/trades"
                            r = await client.get(url, params={"asset_id": asset_id, "limit": 50}, timeout=10)
                            if r.status_code == 200:
                                for trade in r.json():
                                    proxy = trade.get("proxyWallet")
                                    if proxy and proxy not in known_wallets:
                                        new_wallets.add(proxy)
                        except Exception as e:
                            logger.debug(f"Snowball trade scan error: {e}")

                except Exception as e:
                    logger.debug(f"Snowball error for {addr[:10]}...: {e}")

        logger.info(f"Snowball discovered {len(new_wallets)} new candidate wallets")
        return new_wallets