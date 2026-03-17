import asyncio
import os
import sys
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from loguru import logger

# Add backend to path
backend_path = os.path.join(os.getcwd(), "backend")
if os.path.exists(backend_path):
    sys.path.append(backend_path)
else:
    sys.path.append(os.getcwd())

# Load environment variables before anything else
load_dotenv(os.path.join(backend_path if os.path.exists(backend_path) else os.getcwd(), ".env"))

from app.core.config import settings
# from app.engines.tracker.tracker import SmartMoneyTracker
# from app.engines.tracker.cluster_detector import ClusterDetector
from app.engines.autonomous.director import director
from app.engines.arbitrage.manager import arb_manager
from app.engines.weather import weather_manager
from app.engines.rewards.grinder import rewards_manager
from app.engines.council.cache import council_cache


# ─────────────────────────────────────────────────────────────────────────────
# DYNAMIC SCHEDULER
# Tracks when each market was last analyzed and enforces TTL based on
# how close the market is to its resolution date.
# Markets near resolution get frequent re-analysis.
# Markets far from resolution are skipped until their TTL expires.
# ─────────────────────────────────────────────────────────────────────────────

class MarketScheduler:
    """
    Assigns re-analysis frequency to each market based on its time-to-close.

    TTL tiers:
      > 7 days remaining  → re-analyze every 4 hours
      1–7 days remaining  → re-analyze every 1 hour
      6–24 hours          → re-analyze every 15 minutes
      < 6 hours           → re-analyze every 5 minutes
      WHALE signal        → always re-analyze immediately (no TTL)
    """

    # (max_hours_remaining, ttl_seconds, label)
    TIERS = [
        (6,    5 * 60,      "CRITICAL  (<6h)  → every 5min"),
        (24,   15 * 60,     "HOT       (<24h) → every 15min"),
        (168,  60 * 60,     "WARM      (<7d)  → every 1h"),
        (None, 4 * 3600,    "COLD      (>7d)  → every 4h"),
    ]

    def __init__(self):
        # market_id → last_analyzed datetime (UTC)
        self._last_seen: dict[str, datetime] = {}

    def _ttl_for_market(self, end_date_str: str | None) -> tuple[int, str]:
        """Return (ttl_seconds, tier_label) for a market based on its end_date."""
        if not end_date_str:
            return 60 * 60, "UNKNOWN   (no end date) → every 1h"

        try:
            # Accept ISO strings with or without timezone
            if end_date_str.endswith("Z"):
                end_date_str = end_date_str[:-1] + "+00:00"
            end_dt = datetime.fromisoformat(end_date_str)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return 60 * 60, "UNKNOWN   (bad date format) → every 1h"

        now = datetime.now(timezone.utc)
        hours_remaining = (end_dt - now).total_seconds() / 3600

        if hours_remaining <= 0:
            # Already past end date — skip entirely, market should resolve soon
            return 0, "EXPIRED   (past end date) → skip"

        for max_h, ttl, label in self.TIERS:
            if max_h is None or hours_remaining <= max_h:
                return ttl, label

        return 4 * 3600, "COLD      (fallback)"

    def should_analyze(self, market_id: str, end_date_str: str | None,
                       source: str = "INDEXER_DISCOVERY") -> bool:
        """
        Returns True if the market should be re-analyzed this cycle.
        WHALE_TRACKER signals always pass through immediately.
        """
        # Whale signals bypass scheduler — always analyze
        if source == "WHALE_TRACKER":
            return True

        ttl, label = self._ttl_for_market(end_date_str)

        # Expired markets — skip
        if ttl == 0:
            logger.debug(f"[SCHEDULER] Skipping expired market {market_id}")
            return False

        last = self._last_seen.get(market_id)
        if last is None:
            # Never seen before — always analyze
            return True

        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        due = elapsed >= ttl

        if not due:
            remaining = int(ttl - elapsed)
            logger.debug(
                f"[SCHEDULER] Skipping {market_id[:12]}... "
                f"({label.split('→')[0].strip()}, next in {remaining}s)"
            )

        return due

    def mark_analyzed(self, market_id: str):
        """Record that a market was analyzed right now."""
        self._last_seen[market_id] = datetime.now(timezone.utc)

    def log_tier(self, market_id: str, end_date_str: str | None):
        """Log the assigned tier for a market (for debugging)."""
        _, label = self._ttl_for_market(end_date_str)
        logger.debug(f"[SCHEDULER] {market_id[:16]}... → {label}")

    def stats(self) -> dict:
        """Return scheduler statistics."""
        return {
            "tracked_markets": len(self._last_seen),
            "oldest_entry": min(self._last_seen.values(), default=None),
        }

    def purge_old_entries(self, max_age_hours: int = 48):
        """Remove entries older than max_age_hours to prevent memory growth."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        before = len(self._last_seen)
        self._last_seen = {
            mid: ts for mid, ts in self._last_seen.items() if ts > cutoff
        }
        purged = before - len(self._last_seen)
        if purged > 0:
            logger.debug(f"[SCHEDULER] Purged {purged} stale entries.")


# ─────────────────────────────────────────────────────────────────────────────
# OUTCOME RESOLVER
# Checks PENDING trades in autonomous_logs and resolves them to WIN/LOSS
# by querying the Gamma API for final market prices.
# Runs once per cycle before Discovery to keep calibration data fresh.
# ─────────────────────────────────────────────────────────────────────────────

class OutcomeResolver:
    """
    Resolves PENDING trades in autonomous_logs to WIN or LOSS.

    Resolution logic (mirrors backfill_correctness.py):
      best_ask >= 0.98  → WIN  (market resolved YES, position was YES)
      best_ask <= 0.02  → LOSS (market resolved NO)
      intermediate      → remains PENDING

    Only resolves trades older than min_age_minutes to avoid
    checking markets that just entered and haven't resolved yet.
    """

    GAMMA_BASE = "https://gamma-api.polymarket.com"
    WIN_THRESHOLD  = 0.98
    LOSS_THRESHOLD = 0.02
    BATCH_SIZE     = 100  # Increased to clear backlog faster
    MIN_AGE_MINUTES = 120  # Only check trades older than 2 hours

    def __init__(self):
        self._supabase = None

    def _get_supabase(self):
        if self._supabase is None:
            from supabase import create_client
            self._supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return self._supabase

    async def resolve_pending(self) -> dict:
        """
        Main entry point. Fetches PENDING trades, queries Gamma, updates Supabase.
        Returns summary dict with counts.
        """
        import httpx
        sb = self._get_supabase()

        # Fetch PENDING trades: prioritize those whose market end_date has already passed.
        # Markets with end_date_iso=NULL (long-running/unknown) are processed last.
        now_iso = datetime.now(timezone.utc).isoformat()
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=self.MIN_AGE_MINUTES)).isoformat()
        try:
            # Try first: markets with a known end_date that has already passed
            rows = (
                sb.table("autonomous_logs")
                .select("id, market_id, correct, detected_at, end_date_iso")
                .eq("correct", "PENDING")
                .eq("decision", "WOULD_EXECUTE")
                .lt("detected_at", cutoff)
                .lt("end_date_iso", now_iso)
                .order("end_date_iso", desc=False)
                .limit(self.BATCH_SIZE)
                .execute()
            ).data

            # If no expired markets, fall back to NULL end_date markets (check via API)
            if not rows:
                rows = (
                    sb.table("autonomous_logs")
                    .select("id, market_id, correct, detected_at, end_date_iso")
                    .eq("correct", "PENDING")
                    .eq("decision", "WOULD_EXECUTE")
                    .lt("detected_at", cutoff)
                    .is_("end_date_iso", "null")
                    .limit(self.BATCH_SIZE)
                    .execute()
                ).data
        except Exception as e:
            logger.error(f"[RESOLVER] Failed to fetch PENDING trades: {e}")
            return {"checked": 0, "wins": 0, "losses": 0, "still_pending": 0, "errors": 1}

        if not rows:
            logger.debug("[RESOLVER] No PENDING trades to resolve this cycle.")
            return {"checked": 0, "wins": 0, "losses": 0, "still_pending": 0, "errors": 0}

        wins = losses = still_pending = errors = 0
        updates = []

        async with httpx.AsyncClient(timeout=8.0) as client:
            for row in rows:
                market_id = row.get("market_id")
                row_id    = row.get("id")
                if not market_id or not row_id:
                    errors += 1
                    continue
                try:
                    r = await client.get(f"{self.GAMMA_BASE}/markets/{market_id}")
                    if r.status_code != 200:
                        logger.debug(f"[RESOLVER] Market {market_id} returned {r.status_code} — skipping.")
                        still_pending += 1
                        continue

                    data = r.json()
                    is_closed = data.get("closed", False)
                    resolved_price = None

                    # 1. If market is closed, PRIORITIZE outcomePrices (resolution values)
                    if is_closed:
                        outcome_prices = data.get("outcomePrices")
                        if outcome_prices:
                            try:
                                prices = json.loads(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
                                if prices and len(prices) > 0:
                                    resolved_price = float(prices[0])
                                    logger.debug(f"[RESOLVER] Market {market_id} CLOSED. Using resolution price: {resolved_price}")
                            except Exception:
                                pass

                    # 2. Fallback to bestAsk if not closed or resolution price couldn't be parsed
                    if resolved_price is None:
                        raw_ask = data.get("bestAsk") or data.get("best_ask")
                        if raw_ask is not None:
                            try:
                                resolved_price = float(raw_ask)
                            except (ValueError, TypeError):
                                pass

                    if resolved_price is None:
                        still_pending += 1
                        continue

                    if resolved_price >= self.WIN_THRESHOLD:
                        updates.append({"id": row_id, "correct": "WIN"})
                        wins += 1
                    elif resolved_price <= self.LOSS_THRESHOLD:
                        updates.append({"id": row_id, "correct": "LOSS"})
                        losses += 1
                    else:
                        still_pending += 1


                except Exception as e:
                    logger.debug(f"[RESOLVER] Error resolving market {market_id}: {e}")
                    errors += 1

        # Batch update Supabase
        if updates:
            try:
                for upd in updates:
                    sb.table("autonomous_logs").update(
                        {"correct": upd["correct"]}
                    ).eq("id", upd["id"]).execute()
                logger.info(
                    f"[RESOLVER] Resolved {len(updates)} trades: "
                    f"{wins} WIN, {losses} LOSS | "
                    f"{still_pending} still pending | {errors} errors"
                )
            except Exception as e:
                logger.error(f"[RESOLVER] Supabase batch update failed: {e}")
                errors += len(updates)
                wins = losses = 0

        return {
            "checked":       len(rows),
            "wins":          wins,
            "losses":        losses,
            "still_pending": still_pending,
            "errors":        errors,
        }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────

async def autonomous_loop():
    load_dotenv()

    logger.info("STARTING AUTONOMOUS TRADING ENGINE")
    logger.info(f"Mode: {'REAL MONEY' if not settings.COPY_SIMULATION else 'SIMULATION'}")
    logger.info(f"AI Model: {settings.AI_MODEL}")
    logger.info(f"Budget Protection: {settings.GLOBAL_STOP_LOSS_PCT*100}% Stop Loss")
    logger.info(f"Rewards Farming: {'ENABLED' if settings.ENABLE_REWARDS_FARMING else 'DISABLED'}")
    logger.info("Dynamic Scheduler: ENABLED")
    logger.info("  <6h  → every 5min | <24h → every 15min | <7d → every 1h | >7d → every 4h")

    # SmartMoneyTracker and ClusterDetector disabled (Incompatible with whale activity)
    # tracker = SmartMoneyTracker()
    # detector = ClusterDetector(min_wallets=settings.AUTONOMOUS_MIN_WALLETS or 2)
    scheduler = MarketScheduler()
    resolver  = OutcomeResolver()
    # Dummy indexer for Discovery Mode
    from app.engines.tracker.indexer import PolymarketIndexer
    indexer = PolymarketIndexer()

    cycle_count = 0
    while True:
        try:
            start_time = datetime.now(timezone.utc)
            logger.info(f"--- Cycle {cycle_count} Start: {start_time.isoformat()} ---")

            # ── Step 0: Outcome Resolver ──────────────────────────────────────
            # Resolves PENDING trades to WIN/LOSS by checking Gamma API prices.
            # Runs every cycle but only processes trades older than 2h in batches of 20.
            try:
                resolver_result = await resolver.resolve_pending()
                if resolver_result["checked"] > 0:
                    logger.info(
                        f"Step 0: Resolver checked {resolver_result['checked']} trades → "
                        f"{resolver_result['wins']}W / {resolver_result['losses']}L / "
                        f"{resolver_result['still_pending']} pending"
                    )
                else:
                    logger.debug("Step 0: Resolver — no PENDING trades to process.")
            except Exception as resolver_e:
                logger.error(f"Step 0: Resolver error (non-fatal): {resolver_e}")

            # ── Step 1: Update Smart Money List (DISABLED) ────────────────────
            # if cycle_count % 10 == 0:
            #     logger.info("Step 1: Updating Smart Money List...")
            #     await tracker.update_smart_money_list()
            # else:
            #     logger.info(
            #         f"Step 1: Skipping Smart Money update "
            #         f"(Next in {10 - (cycle_count % 10)} cycles)"
            #     )
            logger.info("Step 1: Smart Money Tracker is DISABLED.")

            # ── Step 2: Whale Activity Tracking (DISABLED) ──────────────────────
            logger.info("Step 2: Whale Activity Tracking is DISABLED.")
            # whale_alerts = await detector.scan_for_clusters()
            # ... rest of whale logic commented out ...
            whale_analyzed = 0

            # ── Step 3: Discovery Mode with Dynamic Scheduler ─────────────────
            logger.info("Step 3: Discovery Mode (Hybrid freshest/volume feed)...")
            top_markets = await indexer.get_top_markets(limit=15)

            processed_discovery = 0
            skipped_scheduler = 0

            for m in top_markets:
                market_id = m.get("id", "")
                end_date = m.get("end_date_iso")

                # ── SCHEDULER CHECK ──
                if not scheduler.should_analyze(market_id, end_date, "INDEXER_DISCOVERY"):
                    skipped_scheduler += 1
                    continue

                # Resolve token_id
                token_ids = m.get("clobTokenIds", [])
                if isinstance(token_ids, str):
                    try:
                        token_ids = json.loads(token_ids)
                    except Exception:
                        token_ids = []
                tid = token_ids[0] if token_ids else ""
                if not tid:
                    continue

                discovery_alert = {
                    "market_id": market_id,
                    "market_question": m.get("question"),
                    "token_id": tid,
                    "outcome": "YES",
                    "confidence": 0.50,  # Neutral — Council decides
                    "end_date": end_date,
                    "whale_count": 0,
                    "source": "INDEXER_DISCOVERY",
                    "clob_best_ask": m.get("clob_best_ask"),
                    "clob_best_bid": m.get("clob_best_bid"),
                    "clob_spread": m.get("clob_spread"),
                }
                await director.evaluate_and_execute(discovery_alert)
                scheduler.mark_analyzed(market_id)
                processed_discovery += 1

            # Log scheduler efficiency
            total_candidates = len(top_markets)
            if skipped_scheduler > 0:
                logger.info(
                    f"Scheduler: {skipped_scheduler}/{total_candidates} markets skipped "
                    f"(TTL not expired) | {processed_discovery} analyzed"
                )

            # ── Cycle summary ─────────────────────────────────────────────────
            if whale_analyzed > 0:
                logger.success(f"Cycle Result: {whale_analyzed} Whale-led analysis chains.")
            if processed_discovery > 0:
                logger.info(f"Cycle Result: {processed_discovery} Discovery markets analyzed.")
            if whale_analyzed == 0 and processed_discovery == 0:
                logger.warning("Cycle Result: No actionable markets found.")

            # ── Step 4: Arbitrage Engine ──────────────────────────────────────
            if settings.ENABLE_ARBITRAGE:
                logger.info("Step 4: Running Arbitrage Engine...")
                try:
                    arb_opportunities = await arb_manager.scan_all()
                    if arb_opportunities:
                        logger.success(
                            f"Arbitrage: {len(arb_opportunities)} opportunities! "
                            f"Executing top 3..."
                        )
                        for opp in arb_opportunities[:3]:
                            result = await arb_manager.execute(opp)
                            logger.info(f"Arbitrage Execution: {result}")
                    else:
                        logger.info("Arbitrage: Market efficient this cycle. No opportunities.")
                except Exception as arb_e:
                    logger.error(f"Arbitrage Engine Error: {arb_e}")
            else:
                logger.info("Step 4: Arbitrage Engine DISABLED.")

            # ── Step 5: Rewards Farming ───────────────────────────────────────
            if settings.ENABLE_REWARDS_FARMING:
                logger.info("Step 5: Managing Liquidity Rewards (The Grinder)...")
                await rewards_manager.monitor_active_farms()
                if len(rewards_manager.active_farms) < settings.REWARDS_MAX_MARKETS:
                    await rewards_manager.scan_and_farm(limit=settings.REWARDS_MAX_MARKETS)

            # ── Step 6: Weather Engine ────────────────────────────────────────
            if settings.ENABLE_WEATHER_EXP:
                try:
                    await weather_manager.scan_and_exploit()
                except Exception as we_e:
                    logger.error(f"Weather Engine Error: {we_e}")

            # ── Step 7: Cache maintenance ─────────────────────────────────────
            council_cache.cleanup_expired()
            stats = council_cache.get_stats()
            logger.info(
                f"Council Cache: {stats['hit_rate']} hit rate | "
                f"{stats['daily_calls']} calls today | "
                f"{stats['cached_markets']} markets cached | "
                f"{stats['tokens_saved']} tokens saved ({stats['cost_saved']})"
            )

            # ── Step 8: Scheduler maintenance (every 50 cycles ~50min) ───────
            if cycle_count % 50 == 0:
                scheduler.purge_old_entries(max_age_hours=48)
                sched_stats = scheduler.stats()
                logger.info(
                    f"Scheduler Stats: {sched_stats['tracked_markets']} markets tracked"
                )

            # ── Sleep ─────────────────────────────────────────────────────────
            cycle_count += 1
            # Base cycle is still 60s — the scheduler skips markets internally
            # rather than changing the outer loop frequency
            sleep_seconds = 60
            logger.info(f"--- Cycle Complete. Sleeping {sleep_seconds}s ---")
            await asyncio.sleep(sleep_seconds)

        except KeyboardInterrupt:
            logger.warning("Autonomous Loop stopped by user.")
            break
        except Exception as e:
            logger.error(f"CRITICAL LOOP ERROR: {e}")
            logger.info("Restarting loop in 60s...")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(autonomous_loop())
