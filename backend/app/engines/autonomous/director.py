from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import re
from loguru import logger
from app.core.config import settings
from app.engines.council.orchestrator import AgentOrchestrator
from app.engines.council.cache import council_cache
from app.engines.tracker.copy_executor import CopyExecutor, CopyTradeRequest
from app.services.telegram_bot import telegram
from app.engines.wallet.manager import wallet_manager

class DirectorAgent:
    """
    Autonomous Director: The brain that connects detection (Tracker) with reasoning (Council)
    and execution (Wallet).
    """
    
    def __init__(self):
        self.council = AgentOrchestrator()
        self.executor = CopyExecutor()
        self.min_confidence = settings.AUTONOMOUS_CONFIDENCE_THRESHOLD
        self._traded_markets_cache = set() # Optional in-memory cache

    @property
    def enabled(self):
        # Allow API override
        from app.engines.autonomous.router import RUNTIME_OVERRIDE
        return RUNTIME_OVERRIDE.get("enabled", settings.ENABLE_AUTONOMOUS_TRADING)

    async def check_circuit_breaker(self) -> bool:
        """
        Validates if trading is safe based on Global PnL and Daily Limits.
        Currently enforces:
        1. Daily Spend Limit (via CopyExecutor state)
        2. Global Emergency Stop (via ENV or DB flag)
        """
        try:
            # 1. Check Global Emergency Flag in DB (e.g. system_settings)
            # For now, we trust the ENABLE_AUTONOMOUS_TRADING check which happens before this.
            
            # 2. Check Daily Spend Limit (Proxy for 'Loss' in simulation)
            status = self.executor.get_status()
            if status['remaining_today'] <= 0:
                logger.warning(f"Director: Daily budget exhausted (${status['spent_today']} spent). Halting.")
                return False
            
            # 3. Real PnL Check (Future Implementation)
            # We need a 'portfolio_snapshots' table to track NAV over time.
            # For now, we assume GREEN if the Daily Limit isn't hit in the Executor.
            
            return True 
            
        except Exception as e:
            logger.error(f"Circuit Breaker Error: {e}")
            return False # Fail safe

    async def evaluate_and_execute(self, cluster_alert: Dict) -> Dict:
        """
        Main decision loop with Logging
        """
        market_id = cluster_alert.get("market_id")
        question = cluster_alert.get("market_question") or ""
        outcome = cluster_alert.get("outcome") or "YES"
        token_id = cluster_alert.get("token_id")

        # Guard: token_id is mandatory — without it we can't query the orderbook
        if not token_id:
            logger.debug("Director: Skipping alert with no token_id.")
            return {"status": "skipped", "reason": "no_token_id"}

        if not self.enabled:
            # logger.info(f"Director: Skipping auto-trade for {market_id} (Autonomous Mode DISABLED)")
            return {"status": "skipped", "reason": "disabled"}

        # 0. Circuit Breaker Check (Global Stop-Loss / Take-Profit)
        if not await self.check_circuit_breaker():
            logger.critical("Director: CIRCUIT BREAKER TRIGGERED. Halting operations.")
            return {"status": "halted", "reason": "circuit_breaker"}
            
        # 1. Budget Protection: Frequency Cap handled at loop level
        now = datetime.now(timezone.utc)
        self.last_analysis_time = now

        # Pre-compute q_lower once — used throughout the function
        q_lower = question.lower()

        # ── EARLY EXIT: Category Filter (Zero-cost gate) ──────────────────────
        # Applied BEFORE any API calls or Council queries to save tokens & latency.
        # Updated 2026-03-10: NBA (EV=-0.162, n=234) and Tennis (EV=-0.269, n=75)
        # Updated 2026-03-11: "up or down", box office, tweets added (audit 48h).
        # Updated 2026-03-30: reach $, hit $, market cap, fdv, exact temperature
        #   added after Supabase monitoring revealed filter escapes.
        _esports_kw = [
            "dota 2", "counter-strike", "valorant", "lol:", "league of legends",
            "map 1 winner", "map 2 winner", "map handicap", "esports",
            "astral", "mindfreak", "bounty hunters esports",
        ]
        _nba_kw = [
            "nba", " vs ", " vs. ", "76ers", "sixers", "celtics", "lakers",
            "warriors", "knicks", "nets", "bucks", "heat", "nuggets", "suns",
            "clippers", "grizzlies", "thunder", "mavs", "mavericks", "spurs",
            "rockets", "pistons", "pacers", "hawks", "hornets", "wizards",
            "magic", "raptors", "cavaliers", "cavs", "timberwolves", "wolves",
            "jazz", "pelicans", "kings", "blazers", "trail blazers", "okc",
            "bulls", "basketball", "points scored", "total points",
        ]
        _tennis_kw = [
            "tennis", " atp ", "wta ", "grand slam", "wimbledon", "roland garros",
            "us open", "australian open", "djokovic", "alcaraz", "sinner",
            "medvedev", "swiatek", "sabalenka", "zverev", "rublev",
            "bnp paribas open", "dubai tennis", "indian wells", "miami open",
            "itf ", "challenger ", "kigali", "antalya",
        ]
        _unpredictable_kw = [
            "up or down", "up/down",
            "price of bitcoin", "price of ethereum", "price of solana", "price of xrp",
            "box office", "opening weekend",
            "mrbeast", "tweets by", "@elonmusk", "elon musk tweet",
            "spread", "handicap", "over/under", "o/u",
            "ncaa", "cornhuskers", "boilermakers", "purdue", "nebraska",
            # Price target verbs (2026-03-30) — catch "reach $", "hit $", etc.
            "reach $", "hit $", "exceed $", "surpass $", "cross $",
            # Crypto market cap / FDV markets (2026-03-30)
            "market cap", " fdv", ">$", "one day after launch",
        ]
        _price_kw = [
            "close above $", "close below $", "be above $", "be below $",
            "be between $", "nvidia", "nvda", "share price", "stock price",
            "above $180", "above $66,000", "above $100,000",
        ]
        # Exact temperature markets (2026-03-30): "be X°C on" / "be X°F on"
        # Council cannot predict exact degrees — only ranges have edge.
        # Exception: markets with "between" (range) are kept.
        import re as _re
        _is_exact_temp = (
            bool(_re.search(r'be \d+°[cf] (on|in)', q_lower)) and
            "between" not in q_lower and
            "above" not in q_lower and
            "below" not in q_lower and
            "or below" not in q_lower and
            "or above" not in q_lower
        )

        _excluded_reason = None
        if any(k in q_lower for k in _esports_kw):
            _excluded_reason = "esports_category"
        elif any(k in q_lower for k in _nba_kw):
            _excluded_reason = "nba_excluded_ev_negative"
        elif any(k in q_lower for k in _tennis_kw):
            _excluded_reason = "tennis_excluded_ev_negative"
        elif any(k in q_lower for k in _unpredictable_kw):
            _excluded_reason = "unpredictable_variancy_excluded"
        elif _is_exact_temp:
            _excluded_reason = "exact_temperature_excluded"
        elif ("win on 2026-" in q_lower
              and "both teams" not in q_lower
              and "o/u" not in q_lower
              and "spread" not in q_lower):
            _excluded_reason = "football_direct_winner"
        elif any(k in q_lower for k in _price_kw):
            _excluded_reason = "specific_price_target"

        if _excluded_reason:
            logger.debug(f"Director: [{_excluded_reason}] early-exit for '{question[:50]}' — no Council call.")
            return {"status": "skipped", "reason": _excluded_reason}
        # ─────────────────────────────────────────────────────────────────────

        source = cluster_alert.get("source", "UNKNOWN")
        logger.info(f"Director: Analyzing opportunity [Source: {source}] on '{question}' ({outcome})")
        
        # 1.5 Temporal Safety: Skip if market is stale (handles ET time strings)
        now_utc = datetime.now(timezone.utc)
        
        def is_stale_et(title, current_utc):
            title_lower = title.lower()
            # Hunt for patterns like "11:15pm et" or "10:00pm et"
            time_match = re.findall(r'(\d{1,2}:\d{2}(?:am|pm))\s*et', title_lower)
            if not time_match:
                return False # No ET time found, let it pass to other filters
            
            # Use the last time mentioned (usually the end of the window)
            last_time_str = time_match[-1]
            
            # Extract Month Day for context (e.g., "February 16")
            months = ["january", "february", "march", "april", "may", "june", 
                      "july", "august", "september", "october", "november", "december"]
            m_idx = -1
            m_day = -1
            for i, m in enumerate(months):
                if m in title_lower:
                    m_idx = i + 1
                    day_match = re.search(fr'{m}\s+(\d{{1,2}})', title_lower)
                    if day_match: m_day = int(day_match.group(1))
                    break
            
            if m_idx == -1 or m_day == -1: return False
            
            try:
                # Convert "11:15pm" to 23:15
                time_obj = datetime.strptime(last_time_str.upper(), "%I:%M%p")
                # Construct combined naive datetime in EST (UTC-5 in Feb)
                market_est = datetime(2026, m_idx, m_day, time_obj.hour, time_obj.minute)
                # Convert to UTC: EST + 5 hours = UTC
                market_utc = market_est.replace(tzinfo=None) + timedelta(hours=5)
                market_utc = market_utc.replace(tzinfo=timezone.utc)
                
                # If current time is past market end time + small buffer (2 mins)
                if current_utc > market_utc + timedelta(minutes=2):
                    return True
            except:
                pass
            return False

        if is_stale_et(question, now_utc):
            logger.info(f"Director: Skipping EXPIRED market '{question}' (Past ET Time Detected)")
            return {"status": "skipped", "reason": "expired_et_time"}

        # 1.6 General Date Filter
        months = ["january", "february", "march", "april", "may", "june", 
                  "july", "august", "september", "october", "november", "december"]
        current_month_name = months[now_utc.month-1]
        # q_lower already defined above
        
        if current_month_name in q_lower:
            for day in range(1, now_utc.day):
                # Use regex with word boundaries to avoid matching "February 2" against "February 28"
                if re.search(fr'\b{current_month_name}\s+{day}\b', q_lower):
                    # Double check if it has a time, if it did, the filter above already handled it.
                    if "et" not in q_lower:
                        logger.info(f"Director: Skipping STALE market '{question}' (Past Date Detected: {current_month_name} {day})")
                        return {"status": "skipped", "reason": "stale_date"}

        # 1.7 Deduplication: Avoid trading the same market twice in a short window
        try:
            from supabase import create_client
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            recent_trade = supabase.table("autonomous_logs") \
                .select("id") \
                .eq("market_id", market_id) \
                .in_("decision", ["EXECUTED", "WOULD_EXECUTE"]) \
                .gte("detected_at", (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()) \
                .execute()
            
            if recent_trade.data:
                logger.info(f"Director: Skipping {market_id} - Already logged in the last 12 hours.")
                return {"status": "skipped", "reason": "already_executed_recently"}
        except Exception as e:
            logger.warning(f"Director: Could not check trade history: {e}")

        # 1.8 Fetch Full Market Data (Gamma) & Strict 24h Filter
        description = cluster_alert.get("description", "")
        # Always try to fetch fresh data to check end_date and get canonical ID
        try:
            import httpx
            # Determine best ID for lookup
            # If we have token_id (asset ID), use it - most reliable for positions
            if token_id and len(token_id) > 10:
                params = {"clob_token_ids": token_id}
                url = "https://gamma-api.polymarket.com/markets"
            # Fallback to condition_id (market_id from cluster), usually returns multiple markets
            elif len(market_id) > 10: 
                params = {"condition_id": market_id}
                url = "https://gamma-api.polymarket.com/markets"
            else:
                # Numeric ID
                params = {}
                url = f"https://gamma-api.polymarket.com/markets/{market_id}"
                
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, timeout=10.0)
                if resp.status_code == 200:
                    m_data = resp.json()
                    # Gamma returns list for query params, dict for direct ID
                    if isinstance(m_data, list):
                        if not m_data: 
                            logger.warning(f"Director: No market found for ID {market_id}")
                            return {"status": "skipped", "reason": "market_not_found"}
                        m_data = m_data[0]
                    
                    is_closed = m_data.get("closed")
                    is_active = m_data.get("active")
                    if is_closed in [True, "true", "True"] or is_active in [False, "false", "False"]:
                        logger.info(f"Director: Skipping closed/inactive market '{m_data.get('question', 'Unknown')}'")
                        return {"status": "skipped", "reason": "market_closed"}

                    # 1. Update to Canonical Market ID
                    original_id = market_id
                    market_id = m_data.get("id") # The integer ID (e.g. "12345")
                    if not market_id:
                        market_id = original_id # Fallback
                        
                    question = m_data.get("question", "Unknown Market")
                    description = m_data.get("description", "")
                    
                    # Capture Gamma prices for fallback
                    gamma_best_ask = m_data.get("bestAsk")
                    gamma_best_bid = m_data.get("bestBid")
                    
                    end_date_iso = m_data.get("end_date_iso") or m_data.get("endDate")
                    
                    # 2. Strict Expiration Filter
                    if end_date_iso:
                        try:
                            # Handle ISO format with Z or timezone
                            end_date = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
                            if end_date.tzinfo is None:
                                end_date = end_date.replace(tzinfo=timezone.utc)
                            time_to_end = end_date - datetime.now(timezone.utc)
                            
                            # Skip if the market has already ended (time_to_end is negative)
                            if time_to_end.total_seconds() < 0:
                                logger.info(f"Director: Skipping expired market '{question}' (Ended {abs(time_to_end.days)} days ago).")
                                return {"status": "skipped", "reason": "market_expired"}

                            max_duration_secs = settings.AUTONOMOUS_MAX_MARKET_DURATION_HOURS * 3600
                            if time_to_end.total_seconds() > max_duration_secs:
                                logger.info(f"Director: Skipping long-term market '{question}' (Ends in {time_to_end.days} days). Limit is {settings.AUTONOMOUS_MAX_MARKET_DURATION_HOURS}h.")
                                return {"status": "skipped", "reason": "long_term_market_gt_limit"}
                            
                            logger.info(f"Director: Proceeding with market: '{question}' (Ends in {time_to_end})")
                            
                        except Exception as e:
                            logger.warning(f"Director: Date parsing failed for {end_date_iso}: {e}")
                    else:
                        # Sin fecha de cierre conocida — rechazar para evitar mercados indefinidos
                        logger.info(f"Director: Skipping market without end_date_iso: '{question[:50]}'")
                        return {"status": "skipped", "reason": "no_end_date"}

                    logger.debug(f"Director: Hydrated data. Canonical ID: {market_id}")
                    
        except Exception as e:
            logger.warning(f"Director: Market data fetch failed: {e}")
            # In strict mode, if we can't verify 24h window, we skip
            return {"status": "skipped", "reason": "data_fetch_failed"}

        # 2. Gather Price Intelligence (Optimized: Use pre-validated data from Indexer if available)
        try:
            # CHECK FOR PRE-VALIDATED DATA FIRST
            p_ask = cluster_alert.get("clob_best_ask")
            p_spread = cluster_alert.get("clob_spread")
            p_bid = cluster_alert.get("clob_best_bid")

            if p_ask is not None and p_spread is not None:
                best_ask = p_ask
                best_bid = p_bid
                spread = p_spread
                current_price = best_ask
                logger.debug(f"Director: Using pre-validated CLOB data for '{question[:30]}' (Spread: {spread:.4f}). Skipping redundant API call.")
            else:
                # FALLBACK: Fetch fresh data if not provided (e.g. Whale Tracker alerts)
                intel = await self.executor.client.get_orderbook(token_id)
                best_ask = intel.get("best_ask")
                best_bid = intel.get("best_bid")
                spread = intel.get("spread")
                
                # Check for CLOB error sentinel
                if intel.get("error") or best_ask is None:
                    raise ValueError("CLOB API error sentinel detected")
                
                current_price = best_ask

            # Liquidity Trap Protection: Skip if spread is too wide
            max_spread_limit = settings.PAPER_TRADING_MAX_SPREAD if settings.PAPER_TRADING_MODE else 0.05
            if spread > max_spread_limit:
                logger.warning(f"Director: LIQUIDITY TRAP detected on {question[:30]} (Spread: {spread:.4f} > {max_spread_limit}). Skipping.")
                return {"status": "skipped", "reason": "liquidity_trap", "spread": spread}

            # 3.1 Basic Filters: Price too extreme or already settled?
            price_check = (best_ask + best_bid) / 2 if (best_ask and best_bid) else current_price
            price_limit_low = 0.05 if settings.PAPER_TRADING_MODE else 0.10
            price_limit_high = 0.95 if settings.PAPER_TRADING_MODE else 0.90
            
            if price_check >= price_limit_high or price_check <= price_limit_low:
                logger.info(f"Director: Skipping settled or extreme market '{question}' (Price Check: {price_check:.3f}, best_ask: {best_ask})")
                return {"status": "skipped", "reason": "extreme_price"}

        except Exception as e:
            # TRY GAMMA FALLBACK
            if 'gamma_best_ask' in locals() and gamma_best_ask is not None:
                logger.info(f"Director: CLOB failed/missing, using Gamma fallback price for {token_id}")
                best_ask = float(gamma_best_ask)
                best_bid = float(gamma_best_bid) if gamma_best_bid else (best_ask - 0.01)
                current_price = best_ask
                spread = best_ask - best_bid
            else:
                logger.warning(f"Director: Could not fetch price intelligence for {token_id}, and no Gamma fallback available. Error: {e}")
                return {"status": "skipped", "reason": "price_fetch_failed"}

        whale_count = cluster_alert.get("whale_count", 0)
        
        market_context = {
            "id": market_id,
            "question": question,
            "description": description,
            "outcome": outcome,
            "price": current_price, 
            "best_ask": best_ask,
            "best_bid": best_bid,
            "spread": spread,
            "source": source,
            "whale_count": whale_count,
            "end_date": cluster_alert.get("end_date") or (end_date_iso if 'end_date_iso' in locals() else None),
            "spike_magnitude": cluster_alert.get("confidence", 0.5)
        }

        # 3. Consult The Council (with intelligent caching)
        whale_count = cluster_alert.get("whale_count", 0)
        cached = council_cache.get(market_id, current_whale_count=whale_count)
        cache_hit = False

        if cached:
            # ✅ CACHE HIT: Reuse Council score, re-evaluate with fresh price
            score = cached.final_score
            consensus = cached.consensus_data
            # Defensive normalization: ensure cached consensus_data is a dict
            if isinstance(consensus, str):
                import json as _json_cache
                try:
                    consensus = _json_cache.loads(consensus)
                except Exception:
                    consensus = {"final_score": score, "agent_reports": [], "arbiter_report": {}}
            if not isinstance(consensus, dict):
                consensus = {"final_score": score, "agent_reports": [], "arbiter_report": {}}
            cache_hit = True
            logger.info(
                f"Director: Using CACHED score {score:.3f} for '{question[:40]}…' "
                f"(fresh price: {current_price:.3f}, edge: {score - current_price:+.3f})"
            )
        else:
            # ❌ CACHE MISS: Check budget, then call Council
            can_call, budget_msg = council_cache.can_call_council()
            if not can_call:
                logger.warning(f"Director: {budget_msg}. Skipping analysis for '{question[:40]}'.")
                return {"status": "skipped", "reason": "daily_ai_budget_exhausted"}

            consensus = await self.council.get_market_consensus(market_context)
            # Defensive normalization: ensure consensus is always a dict
            if not isinstance(consensus, dict):
                logger.warning(f"Director: Council returned non-dict ({type(consensus).__name__}). Wrapping as empty consensus.")
                consensus = {"final_score": 0.0, "agent_reports": [], "arbiter_report": {}}
            score = consensus.get("final_score", 0.0)

            # Cache the result for future cycles
            council_cache.store(
                market_id=market_id,
                market_question=question,
                final_score=score,
                consensus_data=consensus,
                end_date=cluster_alert.get("end_date"),
                whale_count=whale_count,
            )
        
        # 3.5 Prioritize Imminent Events (< 48h)
        end_date_str = cluster_alert.get("end_date")
        required_confidence = self.min_confidence
        is_imminent = False
        
        time_remaining = None
        if end_date_str:
            try:
                # end_date is usually ISO "2026-02-18T23:59:59Z" or "2026-02-18"
                # Polymarket API usually sends "2026-02-16T21:00:00.000Z"
                if "T" in end_date_str:
                    end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                else:
                    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                
                time_diff = end_dt - now_utc
                time_remaining = time_diff

                # A. IMMINENT EVENT LOGIC (< 48h)
                if timedelta(hours=0) < time_diff < timedelta(hours=48):
                    required_confidence = max(0.45, self.min_confidence - 0.10) # Lower hurdle (Raul: changed floor from 0.55 to 0.45)
                    is_imminent = True
                    logger.info(f"Director: IMMINENT EVENT ({time_diff}). Lowering threshold to {required_confidence}")

                # B. SNIPING STRATEGY (Short-Term Markets < 60m duration or ending very soon)
                # If market ends in less than 60 mins AND we are not in the last 10 mins -> WAIT
                if timedelta(seconds=0) < time_diff < timedelta(minutes=60):
                     if time_diff > timedelta(minutes=10):
                         logger.info(f"Director: SNIPING MODE. Waiting for last 10m (Current: {time_diff}). Skipping.")
                         return {"status": "skipped", "reason": "sniping_wait_period"}
                     else:
                         logger.info(f"Director: SNIPING MODE ACTIVE. In kill zone (<10m). Execution allowed.")

            except Exception as e:
                logger.warning(f"Director: Could not parse end_date '{end_date_str}': {e}")

        logger.info(f"Director: Council Score: {score:.2f} (Threshold: {required_confidence})")

        # NOTE: CRYPTO ARBITRAGE CHECK block removed 2026-03-30.
        # It was assigning council_score=0.99 (catastrophic zone, EV=-0.584)
        # and overriding the Council without empirical validation.
        # Crypto price markets are now blocked by early exit filters.
        
        # Apply Confidence Max Cap for sizing and safety
        if score > settings.AUTONOMOUS_CONFIDENCE_MAX:
             logger.debug(f"Director: Capping score {score:.3f} to {settings.AUTONOMOUS_CONFIDENCE_MAX} (AUTONOMOUS_CONFIDENCE_MAX)")
             score = settings.AUTONOMOUS_CONFIDENCE_MAX

        # ── NoFolio Sentiment Engine ──────────────────────────────────────────
        # Exploit "Optimism Bias": humans systematically overvalue YES.
        # If the Council is skeptical (low score) but the market price is HIGH,
        # the market is likely inflated by hype → BUY NO instead of skipping.
        # Source: "No-Folio" strategy from research + Plan Maestro.
        nofolio_triggered = False
        nofolio_outcome = outcome  # Will override to "NO" if triggered
        nofolio_token_id = token_id
        
        if (settings.ENABLE_NOFOLIO and
            score < settings.NOFOLIO_MAX_AI_SCORE and
            current_price > settings.NOFOLIO_MIN_MARKET_PRICE):
            
            # Locate the NO token for this market
            try:
                async with __import__('httpx').AsyncClient() as http:
                    from app.core.config import settings as s
                    url = f"{s.GAMMA_API_URL}/markets/{market_id}"
                    resp = await http.get(url, timeout=5)
                    m_data = resp.json() if resp.status_code == 200 else {}
                    import json as _json
                    token_ids_raw = m_data.get("clobTokenIds", "[]")
                    all_tokens = _json.loads(token_ids_raw) if isinstance(token_ids_raw, str) else token_ids_raw
                    
                    if len(all_tokens) >= 2:
                        no_token_id = all_tokens[1]  # Index 1 = NO token
                        no_book = await self.executor.client.get_orderbook(no_token_id)
                        no_ask = no_book.get("best_ask")
                        
                        if no_ask and no_ask < 0.40:  # NO must be cheap (< 40 cents)
                            nofolio_triggered = True
                            nofolio_outcome = "NO"
                            nofolio_token_id = no_token_id
                            current_price = no_ask
                            
                            logger.warning(
                                f"Director: 🎯 NOFOLIO TRIGGERED on '{question[:40]}' | "
                                f"Market YES={best_ask:.3f} (hype inflated) | "
                                f"AI Score={score:.2f} (skeptical) | Buying NO @ {no_ask:.3f}"
                            )
                            score = 0.90  # Treat as high confidence contrarian trade
                            required_confidence = 0.60
            except Exception as nf_e:
                logger.debug(f"Director: NoFolio lookup failed: {nf_e}")
        # ──────────────────────────────────────────────────────────────────────

        # EXECUTE only if Confidence >= Threshold AND Net Edge >= source-specific minimum
        # Raul's Formula: Edge neto = Score - best_ask - (spread * 0.5)
        # This accounts for the liquidity friction of crossing the spread.
        #
        # ── YES/NO Side Evaluation (11 Mar 2026) ─────────────────────────────
        # Empirical data (204,168 Polymarket markets 2024-2026):
        #   NO wins 61.0% of the time globally.
        #   Hardcoding outcome="YES" creates a structural negative bias.
        # Fix: evaluate both sides, pick the one with higher edge_net.
        no_ask = round(1.0 - best_bid, 4) if best_bid else None

        edge_brute_yes = score - current_price
        edge_net_yes   = score - current_price - (spread * 0.5)

        if no_ask is not None:
            no_score      = 1.0 - score  # Council's implicit NO probability
            edge_brute_no = no_score - no_ask
            edge_net_no   = no_score - no_ask - (spread * 0.5)
        else:
            edge_brute_no = edge_net_no = -999.0

        if edge_net_no > edge_net_yes:
            outcome       = "NO"
            edge_brute    = edge_brute_no
            edge_net      = edge_net_no
            current_price = no_ask
            logger.info(
                f"Director: Side=NO selected | "
                f"edge_YES={edge_net_yes:+.3f} < edge_NO={edge_net_no:+.3f} | "
                f"NO ask={no_ask:.3f}"
            )
        else:
            outcome    = "YES"
            edge_brute = edge_brute_yes
            edge_net   = edge_net_yes
            logger.debug(
                f"Director: Side=YES selected | "
                f"edge_YES={edge_net_yes:+.3f} >= edge_NO={edge_net_no:+.3f}"
            )
        
        # ── Source-Differentiated Edge Thresholds ─────────────────────────────
        # WHALE_TRACKER: lower edge required (0.05) because the informational
        #   signal from a smart-money wallet is already valuable alpha on its own.
        # INDEXER_DISCOVERY: strict edge required (settings.PAPER_MIN_EDGE_NET)
        #   because there's no external signal backing the Council's analysis.
        if source == "WHALE_TRACKER":
            effective_min_edge = 0.05  # Smart money signal reduces bar
            logger.info(f"Director: WHALE_TRACKER signal detected — relaxed edge threshold: {effective_min_edge}")
        else:
            effective_min_edge = settings.PAPER_MIN_EDGE_NET  # Full strictness for pure discovery
        
        logger.info(
            f"Director: Edge Brute: {edge_brute:+.3f} | "
            f"Edge Net: {edge_net:+.3f} (Spread Cost: {spread * 0.5:.3f}) | "
            f"Min Edge Required: {effective_min_edge} [Source: {source}]"
        )

        # ── PAPER TRADING MODE ─────────────────────────────────────────────
        # Log WOULD_EXECUTE decisions for calibration without real execution.
        # Captures rich data for later analysis of Council accuracy.
        #
        # DEDUP GUARD: Only log to Supabase if:
        #   (a) First time evaluating this market, OR
        #   (b) Ask price changed by > 0.02 since last log (material change), OR
        #   (c) Decision flipped (WOULD_EXECUTE ↔ PAPER_REJECTED)
        # This prevents flooding Supabase with 800+ duplicate rows per session.
        if settings.PAPER_TRADING_MODE:
            # ── Category Exclusion Filters (Empirically validated 2026-03-10) ──────
            # NBA: EV=-0.162, n=234 — capital destroyer, excluded 2026-03-10
            # Tennis: EV=-0.269, n=75 — capital destroyer, excluded 2026-03-10
            # Up/Down crypto, box office, NCAA spreads: excluded 2026-03-11 (audit 48h)

            # Group 1: eSports
            esports_keywords = [
                "dota 2", "lol:", "league of legends", "counter-strike", "valorant",
                "esports", "dreamleague", "lck", "vct", "cs2", "cs:go",
                "map 1 winner", "map 2 winner", "map handicap", "map winner",
                "astral", "bounty hunters esports", "mindfreak",
            ]
            is_esports = any(kw in q_lower for kw in esports_keywords)

            # Group 2: NBA (EV=-0.162, n=234)
            nba_keywords = [
                "nba", " vs ", " vs. ", "76ers", "sixers", "celtics", "lakers",
                "warriors", "knicks", "nets", "bucks", "heat", "nuggets", "suns",
                "clippers", "grizzlies", "thunder", "mavs", "mavericks", "spurs",
                "rockets", "pistons", "pacers", "hawks", "hornets", "wizards",
                "magic", "raptors", "cavaliers", "cavs", "timberwolves", "wolves",
                "jazz", "pelicans", "kings", "blazers", "okc", "bulls", "basketball",
            ]
            is_nba = any(kw in q_lower for kw in nba_keywords)

            # Group 3: Tennis (EV=-0.269, n=75)
            tennis_keywords = [
                "tennis", " atp ", "wta ", "grand slam", "wimbledon", "roland garros",
                "us open", "australian open", "djokovic", "alcaraz", "sinner",
                "medvedev", "swiatek", "sabalenka", "itf ", "challenger ",
                "kigali", "antalya", "indian wells", "miami open",
            ]
            is_tennis = any(kw in q_lower for kw in tennis_keywords)

            # Group 4: Unpredictable / noise markets (audit 2026-03-11)
            unpredictable_keywords = [
                "up or down", "up/down",
                "price of bitcoin", "price of ethereum", "price of solana",
                "box office", "opening weekend", "mrbeast", "tweets by",
                "spread", "handicap", "over/under", "o/u",
                "ncaa", "cornhuskers", "boilermakers", "purdue", "nebraska",
            ]
            is_unpredictable = any(kw in q_lower for kw in unpredictable_keywords)

            # Group 5: Direct football winner
            is_football_direct_winner = (
                "win on 2026-" in q_lower and
                "both teams" not in q_lower and
                "o/u" not in q_lower and
                "spread" not in q_lower
            )

            # Group 6: Specific crypto/stock price targets
            is_specific_price_target = any(kw in q_lower for kw in [
                "close above $", "close below $", "close at $",
                "be above $", "be below $", "be between $",
                "above $180", "above $66,000", "above $100,000",
                "nvda", "nvidia", "share price", "stock price",
            ])

            excluded_reason = None
            if is_esports:
                excluded_reason = "esports_filter"
            elif is_nba:
                excluded_reason = "nba_excluded_ev_negative"
            elif is_tennis:
                excluded_reason = "tennis_excluded_ev_negative"
            elif is_unpredictable:
                excluded_reason = "unpredictable_variancy_excluded"
            elif is_football_direct_winner:
                excluded_reason = "football_direct_winner_filter"
            elif is_specific_price_target:
                excluded_reason = "specific_price_target_filter"

            is_excluded = excluded_reason is not None
            paper_status = "WOULD_EXECUTE" if (edge_net >= effective_min_edge and not is_excluded) else "PAPER_REJECTED"

            if is_excluded and edge_net >= effective_min_edge:
                logger.info(f"Director: [{excluded_reason}] triggered for '{question[:40]}'. Force rejecting.")
            
            # Extract individual agent scores for calibration
            agent_scores_dict = {}
            agent_reports = consensus.get("agent_reports", [])
            if isinstance(agent_reports, list):
                for r in agent_reports:
                    agent_scores_dict[r.get("agent", "?")] = round(r.get("confidence", 0), 3)
            arbiter_report = consensus.get("arbiter_report")
            if isinstance(arbiter_report, dict):
                agent_scores_dict["RiskArbiter"] = round(arbiter_report.get("confidence", 0), 3)

            logger.info(
                f"[PAPER] {paper_status} | Market: {question[:60]} | "
                f"Council: {score:.3f} | Ask: {best_ask} | Spread: {spread:.3f} | "
                f"Edge Brute: {edge_brute:+.3f} | Edge Net: {edge_net:+.3f} | "
                f"Agents: {agent_scores_dict}"
            )

            # ── Deduplication Guard ──
            # _paper_logged is a class-level dict: {market_id: (last_ask, last_decision)}
            if not hasattr(self, '_paper_logged'):
                self._paper_logged = {}
            
            prev = self._paper_logged.get(market_id)
            should_log = False
            
            if prev is None:
                # (a) First time seeing this market → always log
                should_log = True
                logger.debug(f"[PAPER] New market {market_id}, will log to Supabase.")
            else:
                prev_ask, prev_decision = prev
                price_delta = abs(best_ask - prev_ask) if best_ask and prev_ask else 0
                
                if prev_decision != paper_status:
                    # (c) Decision flipped → log the change
                    should_log = True
                    logger.info(f"[PAPER] Decision FLIPPED for {market_id}: {prev_decision} → {paper_status}. Logging.")
                elif price_delta > 0.02:
                    # (b) Material price change → log update
                    should_log = True
                    logger.info(f"[PAPER] Price changed for {market_id}: {prev_ask:.3f} → {best_ask:.3f} (Δ={price_delta:.3f}). Logging.")
                else:
                    logger.debug(f"[PAPER] Skipping duplicate log for {market_id} (same decision, price Δ={price_delta:.4f} < 0.02)")
            
            if should_log:
                try:
                    from supabase import create_client
                    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                    import json as _json
                    
                    paper_entry = {
                        "market_id": market_id,
                        "market_question": question,
                        "outcome": outcome,
                        "council_score": round(score, 3),
                        "decision": paper_status,
                        "reasoning": _json.dumps(agent_scores_dict),
                        "execution_tx": None,
                        "size_usdc": 0.0,
                        "cache_hit": cache_hit,
                        "best_ask": best_ask,
                        "best_bid": best_bid,
                        "spread": round(spread, 4),
                        "detected_at": datetime.now(timezone.utc).isoformat(),
                        "source": source
                    }
                    supabase.table("autonomous_logs").insert(paper_entry).execute()
                    logger.info(f"[PAPER] Logged {paper_status} for {market_id}")
                    
                    # Update dedup tracker
                    self._paper_logged[market_id] = (best_ask, paper_status)

                except Exception as e:
                    logger.error(f"[PAPER] Failed to log: {e}")
            else:
                logger.info(f"[PAPER] {paper_status} for {market_id} (dedup: skipped Supabase)")

            return {
                "status": paper_status,
                "tx": None,
                "size": 0.0,
                "score": score
            }
        # ── END PAPER TRADING MODE ─────────────────────────────────────────

        # Decision Logic
        decision_status = "REJECTED"
        tx_hash = None
        size_usdc = 0.0

        # Tight Execution Filter: 
        # 1. Score must pass confidence hurdle
        # 2. Net Edge must be at least 3% (0.03) to cover risk/slippage
        if score >= required_confidence and edge_net >= 0.03:
            # 4. Size Position
            base_size = settings.MIN_ORDER_SIZE_USD
            multiplier = 1.0 + (score - required_confidence) * 5
            size_usdc = min(base_size * multiplier, settings.AUTONOMOUS_MAX_SIZE)

            # Use NoFolio overrides if triggered
            exec_token_id = nofolio_token_id if nofolio_triggered else token_id
            exec_outcome = nofolio_outcome if nofolio_triggered else outcome

            # 5. Execute Trade
            user_id = settings.AUTONOMOUS_USER_ID
            if user_id:
                trade_req = CopyTradeRequest(
                    user_id=user_id,
                    source_wallet="Autonomous-Director" + ("-NoFolio" if nofolio_triggered else ""),
                    token_id=exec_token_id,
                    market_id=market_id,
                    market_question=question,
                    outcome=exec_outcome,
                    price=current_price + 0.005, # Tiny buffer above ASK to ensure fill
                    size_usdc=size_usdc
                )
                try:
                    result = await self.executor.execute_copy(trade_req)
                    if result.status in ["success", "simulated"]:
                        decision_status = "EXECUTED"
                        tx_hash = result.order_id
                        
                        # Notify Telegram with Balance
                        try:
                            balance = wallet_manager.get_onchain_balance(settings.POLY_PROXY_ADDRESS) if settings.POLY_PROXY_ADDRESS else 0.0
                            await telegram.trade_executed(
                                market=question,
                                outcome=exec_outcome,
                                score=score,
                                size=size_usdc,
                                sim=result.status == "simulated",
                                balance=balance
                            )
                        except Exception as te:
                            logger.error(f"Telegram execution notification failed: {te}")
                    else:
                        decision_status = "FAILED"
                        logger.error(f"Director Execution Failed: {result.message}")
                except Exception as e:
                    decision_status = "ERROR"
                    logger.error(f"Director Exception: {e}")
            else:
                decision_status = "SKIPPED_NO_USER"
                logger.error("Director: No AUTONOMOUS_USER_ID configured.")

        # 6. Log Decision to Supabase
        try:
            from supabase import create_client
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            
            import json as _json_log
            # Always serialize reasoning to a JSON string to avoid Supabase type errors
            try:
                reasoning_serialized = _json_log.dumps(consensus) if isinstance(consensus, dict) else str(consensus)
            except Exception:
                reasoning_serialized = "{}"
            
            log_entry = {
                "market_id": market_id,
                "market_question": question,
                "outcome": outcome,
                "council_score": score,
                "decision": decision_status,
                "reasoning": reasoning_serialized,
                "execution_tx": tx_hash,
                "size_usdc": size_usdc,
                "cache_hit": cache_hit,
                "best_ask": best_ask,
                "best_bid": best_bid,
                "spread": spread,
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "source": source
            }
            supabase.table("autonomous_logs").insert(log_entry).execute()
            logger.info(f"Director: Logged decision {decision_status} for {market_id}")
            
        except Exception as e:
            logger.error(f"Failed to log autonomous decision: {e}")

        return {
            "status": decision_status,
            "tx": tx_hash,
            "size": size_usdc,
            "score": score
        }

director = DirectorAgent()