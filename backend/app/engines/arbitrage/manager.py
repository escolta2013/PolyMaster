"""
Arbitrage Manager — PolyMaster Alpha Engine
============================================
Detects and executes two types of arbitrage on Polymarket:

1. Binary Arbitrage  (Intra-Market)
   - In a binary YES/NO market, YES + NO should always sum to $1.00.
   - If sum < ARB_MAX_SUM (default 0.985), we can buy both and lock in a profit.
   - Example: YES @ 0.49 + NO @ 0.49 = $0.98 → profit of $0.02 per pair.

2. Bundle Arbitrage  (Multi-Outcome / categorical markets)
   - In a categorical market (e.g., "Who wins 2028 election?"), only ONE outcome pays $1.
   - If the SUM of all YES prices < ARB_MAX_SUM, we buy all outcomes and lock in profit.
   - Example: Candidate A=0.35, B=0.30, C=0.20 → Sum=0.85 → $0.15 profit per bundle.

Strategy source: User research + "Arbitrage in Prediction Markets" paper.
"""

from loguru import logger
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import httpx
import json
import asyncio

from app.core.client import PolyClient
from app.core.config import settings


class ArbOpportunity:
    """A detected arbitrage opportunity."""

    def __init__(
        self,
        arb_type: str,   # "binary" or "bundle"
        market_id: str,
        question: str,
        total_cost: float,
        guaranteed_payout: float,
        edge_pct: float,
        outcomes: List[Dict],   # [{outcome, token_id, ask_price}]
    ):
        self.arb_type = arb_type
        self.market_id = market_id
        self.question = question
        self.total_cost = total_cost
        self.guaranteed_payout = guaranteed_payout
        self.edge_pct = edge_pct
        self.outcomes = outcomes
        self.detected_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict:
        return {
            "arb_type": self.arb_type,
            "market_id": self.market_id,
            "question": self.question,
            "total_cost": round(self.total_cost, 4),
            "guaranteed_payout": self.guaranteed_payout,
            "edge_pct": round(self.edge_pct * 100, 2),
            "outcomes": self.outcomes,
            "detected_at": self.detected_at.isoformat(),
        }


class ArbManager:
    """
    Arbitrage Manager — scans for and executes arbitrage opportunities.

    How to use:
    -----------
    arb_manager = ArbManager()
    opportunities = await arb_manager.scan_all()
    for opp in opportunities:
        await arb_manager.execute(opp)
    """

    def __init__(self):
        self.client = PolyClient.get_instance()
        self.gamma_api = settings.GAMMA_API_URL
        self.max_sum = settings.ARB_MAX_SUM
        self.min_edge_pct = settings.ARB_MIN_EDGE_PCT
        self.simulation = settings.COPY_SIMULATION
        self._recent_arbs: Dict[str, datetime] = {}   # market_id → last executed
        self.dedup_window_seconds = 3600  # Don't re-execute same market within 1h

    # ─────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────

    async def scan_all(self) -> List[ArbOpportunity]:
        """
        Master scan: checks both binary and bundle markets.
        Returns a list of detected opportunities sorted by edge (best first).
        """
        opportunities = []

        # Scan 1: Binary markets (YES + NO < 1)
        binary_opps = await self._scan_binary_markets()
        opportunities.extend(binary_opps)

        # Scan 2: Multi-outcome / categorical markets (Sum YES < 1)
        bundle_opps = await self._scan_bundle_markets()
        opportunities.extend(bundle_opps)

        # Sort by edge descending
        opportunities.sort(key=lambda x: x.edge_pct, reverse=True)

        if opportunities:
            logger.success(
                f"Arbitrage: Found {len(opportunities)} opportunities "
                f"({len(binary_opps)} binary, {len(bundle_opps)} bundle)"
            )
        else:
            logger.info("Arbitrage: No profitable opportunities found this cycle.")

        return opportunities

    async def execute(self, opp: ArbOpportunity, budget_usdc: float = None) -> Dict:
        """
        Execute a detected arbitrage opportunity.
        In SIMULATION mode: logs the trade but does NOT send orders.
        In LIVE mode: places limit orders at ask price for every outcome.
        """
        budget = budget_usdc or settings.ARB_MAX_BUDGET_PER_BUNDLE

        # Deduplication: skip if we already executed this market recently
        if self._is_recently_executed(opp.market_id):
            logger.debug(f"Arbitrage: Skipping {opp.market_id} (already executed recently)")
            return {"status": "skipped", "reason": "dedup"}

        # Safety: edge must clear the minimum threshold
        if opp.edge_pct < self.min_edge_pct:
            logger.warning(
                f"Arbitrage: Edge too small ({opp.edge_pct*100:.2f}%) for {opp.question[:40]}. Skipping."
            )
            return {"status": "skipped", "reason": "insufficient_edge"}

        mode = "SIMULATION" if self.simulation else "LIVE"
        logger.info(
            f"Arbitrage [{mode}]: Executing {opp.arb_type.upper()} arb on "
            f"'{opp.question[:50]}' | Cost: ${opp.total_cost:.4f} | "
            f"Payout: ${opp.guaranteed_payout:.2f} | Edge: {opp.edge_pct*100:.2f}%"
        )

        # Calculate how many bundles we can buy with the budget
        num_bundles = max(1, int(budget / opp.total_cost))
        actual_cost = num_bundles * opp.total_cost
        actual_profit = num_bundles * (opp.guaranteed_payout - opp.total_cost)

        results = []
        if self.simulation:
            # Simulation: just log what we WOULD do
            for out in opp.outcomes:
                results.append({
                    "outcome": out["outcome"],
                    "token_id": out["token_id"],
                    "price": out["ask_price"],
                    "size": num_bundles,
                    "status": "simulated",
                })
            logger.success(
                f"Arbitrage [SIM]: Would buy {num_bundles} bundle(s) of "
                f"'{opp.question[:40]}' for ${actual_cost:.2f} → projected profit ${actual_profit:.2f}"
            )
        else:
            # Live execution: place a limit BUY for each outcome
            from app.engines.ghost.order_manager import OrderManager
            order_mgr = OrderManager()
            for out in opp.outcomes:
                res = order_mgr.create_and_post_order(
                    token_id=out["token_id"],
                    price=out["ask_price"],
                    size=float(num_bundles),
                    side="BUY"
                )
                results.append({
                    "outcome": out["outcome"],
                    "token_id": out["token_id"],
                    "price": out["ask_price"],
                    "size": num_bundles,
                    "status": res.get("status"),
                    "order_id": res.get("order_id"),
                })
                await asyncio.sleep(0.3)  # Brief pause between orders

        # Mark as recently executed
        self._mark_executed(opp.market_id)

        # Log to Supabase
        await self._log_to_supabase(opp, results, actual_cost, actual_profit, num_bundles)

        return {
            "status": "executed",
            "arb_type": opp.arb_type,
            "bundles": num_bundles,
            "total_cost": actual_cost,
            "projected_profit": actual_profit,
            "orders": results,
        }

    # ─────────────────────────────────────────────
    # DETECTION LOGIC
    # ─────────────────────────────────────────────

    async def _scan_binary_markets(self) -> List[ArbOpportunity]:
        """
        Scans active binary markets where YES token + NO token prices don't sum to $1.
        Edge condition: best_ask(YES) + best_ask(NO) < ARB_MAX_SUM
        """
        opportunities = []

        try:
            async with httpx.AsyncClient() as http:
                # Fetch active markets with multiple tokens (binary = exactly 2 token IDs)
                url = f"{self.gamma_api}/markets"
                params = {
                    "limit": 100,
                    "order": "volume",
                    "ascending": "false",
                    "active": "true",
                }
                resp = await http.get(url, params=params, timeout=15)
                resp.raise_for_status()
                markets = resp.json()

            logger.info(f"Arbitrage: Scanning {len(markets)} markets for binary arb...")

            # Process in batches to avoid hammering the API
            batch_size = 10
            for i in range(0, len(markets), batch_size):
                batch = markets[i: i + batch_size]
                tasks = [self._check_binary_arb(m) for m in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results:
                    if isinstance(r, ArbOpportunity):
                        opportunities.append(r)

        except Exception as e:
            logger.error(f"Arbitrage: Error during binary scan: {e}")

        return opportunities

    async def _check_binary_arb(self, market: Dict) -> Optional[ArbOpportunity]:
        """Checks a single binary market for YES+NO < $1 arbitrage."""
        try:
            # ── FIX: Skip expired/closed markets before hitting the CLOB API ──
            if market.get("closed") or market.get("archived") or not market.get("active"):
                return None

            end_date_raw = market.get("endDate") or market.get("end_date_iso")
            if end_date_raw:
                try:
                    end_dt = datetime.fromisoformat(end_date_raw.replace("Z", "+00:00"))
                    if end_dt < datetime.now(timezone.utc):
                        return None  # Market already expired — skip to avoid 404
                except Exception:
                    pass  # If parsing fails, proceed cautiously

            token_ids_raw = market.get("clobTokenIds", "[]")
            if isinstance(token_ids_raw, str):
                token_ids = json.loads(token_ids_raw)
            else:
                token_ids = token_ids_raw or []

            # Binary market = exactly 2 tokens (YES and NO)
            if len(token_ids) != 2:
                return None

            yes_id, no_id = token_ids[0], token_ids[1]
            market_id = str(market.get("id", ""))
            question = market.get("question", "")

            # Get orderbooks for both tokens
            yes_book = await self.client.get_orderbook(yes_id)
            no_book = await self.client.get_orderbook(no_id)

            yes_ask = yes_book.get("best_ask")
            no_ask = no_book.get("best_ask")

            if yes_ask is None or no_ask is None:
                return None

            total_cost = yes_ask + no_ask

            if total_cost >= self.max_sum:
                return None  # No edge

            edge_pct = (1.0 - total_cost) / total_cost

            # Filter out negligible edges (below min threshold after fees ~0.5%)
            if edge_pct < self.min_edge_pct:
                return None

            logger.info(
                f"Arbitrage [BINARY FOUND]: '{question[:50]}' | "
                f"YES={yes_ask:.3f} + NO={no_ask:.3f} = {total_cost:.4f} | "
                f"Edge: {edge_pct*100:.2f}%"
            )

            return ArbOpportunity(
                arb_type="binary",
                market_id=market_id,
                question=question,
                total_cost=total_cost,
                guaranteed_payout=1.0,
                edge_pct=edge_pct,
                outcomes=[
                    {"outcome": "YES", "token_id": yes_id, "ask_price": yes_ask},
                    {"outcome": "NO",  "token_id": no_id,  "ask_price": no_ask},
                ],
            )

        except Exception as e:
            logger.debug(f"Arbitrage: Binary check error for market: {e}")
            return None

    async def _scan_bundle_markets(self) -> List[ArbOpportunity]:
        """
        Scans categorical / multi-outcome markets where Sum(YES prices) < $1.
        These are markets where ONLY ONE outcome pays $1.
        """
        opportunities = []

        try:
            async with httpx.AsyncClient() as http:
                # Categorical markets are usually under parent "events"
                # They have > 2 clobTokenIds.
                url = f"{self.gamma_api}/events"
                params = {
                    "limit": 50,
                    "order": "volume",
                    "ascending": "false",
                    "active": "true",
                }
                resp = await http.get(url, params=params, timeout=15)
                resp.raise_for_status()
                events = resp.json()

            logger.info(f"Arbitrage: Scanning {len(events)} events for bundle arb...")

            for event in events:
                markets_in_event = event.get("markets", [])
                # A "categorical bundle" is a group of binary markets under one event
                # where each market is one candidate/option — exactly one will resolve YES.
                if len(markets_in_event) < 3:
                    continue  # Not interesting — need 3+ options for meaningful bundle

                opp = await self._check_bundle_arb(event, markets_in_event)
                if opp:
                    opportunities.append(opp)

        except Exception as e:
            logger.error(f"Arbitrage: Error during bundle scan: {e}")

        return opportunities

    async def _check_bundle_arb(self, event: Dict, markets: List[Dict]) -> Optional[ArbOpportunity]:
        """
        Checks if buying YES on every outcome in a categorical event costs < $1.
        If so, no matter who wins, we get exactly $1 back.
        """
        try:
            # ── FIX: Skip expired/closed events before hitting the CLOB API ──
            if event.get("closed") or event.get("archived") or not event.get("active"):
                return None

            end_date_raw = event.get("endDate") or event.get("end_date_iso")
            if end_date_raw:
                try:
                    end_dt = datetime.fromisoformat(end_date_raw.replace("Z", "+00:00"))
                    if end_dt < datetime.now(timezone.utc):
                        return None  # Event already expired — skip to avoid 404s
                except Exception:
                    pass

            event_title = event.get("title", event.get("slug", "Unknown Event"))
            event_id = str(event.get("id", ""))

            outcomes_data = []
            total_cost = 0.0

            for m in markets:
                # ── FIX: Also skip individual expired/closed sub-markets ──
                if m.get("closed") or m.get("archived") or not m.get("active"):
                    return None

                m_end_raw = m.get("endDate") or m.get("end_date_iso")
                if m_end_raw:
                    try:
                        m_end_dt = datetime.fromisoformat(m_end_raw.replace("Z", "+00:00"))
                        if m_end_dt < datetime.now(timezone.utc):
                            return None  # At least one sub-market expired — bundle invalid
                    except Exception:
                        pass
                
                token_ids_raw = m.get("clobTokenIds", "[]")
                if isinstance(token_ids_raw, str):
                    token_ids = json.loads(token_ids_raw)
                else:
                    token_ids = token_ids_raw or []

                if not token_ids:
                    continue

                yes_token_id = token_ids[0]
                book = await self.client.get_orderbook(yes_token_id)
                ask = book.get("best_ask")

                if ask is None:
                    # If ANY outcome has no liquidity, skip — we can't build the bundle
                    logger.debug(f"Arbitrage: No ask for '{m.get('question','?')[:30]}', skipping event.")
                    return None

                outcomes_data.append({
                    "outcome": m.get("question", "Unknown"),
                    "token_id": yes_token_id,
                    "ask_price": ask,
                })
                total_cost += ask

                await asyncio.sleep(0.1)  # Be gentle with the API

            if len(outcomes_data) < 3:
                return None

            if total_cost >= self.max_sum:
                return None  # No edge

            edge_pct = (1.0 - total_cost) / total_cost

            if edge_pct < self.min_edge_pct:
                return None

            logger.success(
                f"Arbitrage [BUNDLE FOUND]: '{event_title[:50]}' | "
                f"{len(outcomes_data)} outcomes | Sum={total_cost:.4f} | Edge: {edge_pct*100:.2f}%"
            )

            return ArbOpportunity(
                arb_type="bundle",
                market_id=event_id,
                question=event_title,
                total_cost=total_cost,
                guaranteed_payout=1.0,
                edge_pct=edge_pct,
                outcomes=outcomes_data,
            )

        except Exception as e:
            logger.debug(f"Arbitrage: Bundle check error: {e}")
            return None

    # ─────────────────────────────────────────────
    # UTILITY
    # ─────────────────────────────────────────────

    def _is_recently_executed(self, market_id: str) -> bool:
        if market_id not in self._recent_arbs:
            return False
        elapsed = (datetime.now(timezone.utc) - self._recent_arbs[market_id]).total_seconds()
        return elapsed < self.dedup_window_seconds

    def _mark_executed(self, market_id: str):
        self._recent_arbs[market_id] = datetime.now(timezone.utc)

    async def _log_to_supabase(
        self,
        opp: ArbOpportunity,
        orders: List[Dict],
        total_cost: float,
        projected_profit: float,
        num_bundles: int,
    ):
        """Logs the arbitrage execution to autonomous_logs table."""
        try:
            from supabase import create_client
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

            supabase.table("autonomous_logs").insert({
                "market_id": opp.market_id,
                "market_question": f"[ARB-{opp.arb_type.upper()}] {opp.question[:200]}",
                "outcome": "BUNDLE",
                "council_score": opp.edge_pct,
                "decision": "EXECUTED_SIM" if self.simulation else "EXECUTED_LIVE",
                "reasoning": {
                    "arb_type": opp.arb_type,
                    "total_cost": total_cost,
                    "projected_profit": projected_profit,
                    "num_bundles": num_bundles,
                    "outcomes": opp.outcomes,
                    "orders": orders,
                },
                "size_usdc": total_cost,
                "detected_at": opp.detected_at.isoformat(),
            }).execute()

            logger.success(f"Arbitrage: Logged to Supabase: [{opp.arb_type}] {opp.question[:40]}")

        except Exception as e:
            logger.error(f"Arbitrage: Failed to log to Supabase: {e}")


# Singleton instance
arb_manager = ArbManager()
