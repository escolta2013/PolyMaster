"""
whale_alpha_tracker.py
======================
Measures the RAW alpha of Whale Tracker signals WITHOUT Council AI.

This script runs in parallel with the main bot and answers the most
important unanswered question in PolyMaster:

  "Do whale convergence signals have predictive value BY THEMSELVES,
   before the Council AI processes them?"

If YES → the Council AI is adding value on top of a real signal.
If NO  → the system needs a different informational edge.

How it works:
  1. Detects whale cluster signals (same as main loop)
  2. Records: market_id, question, entry_price, whale_count, timestamp
  3. Periodically checks if those markets resolved (price > 0.97 or < 0.03)
  4. Calculates raw accuracy: did the market resolve in the direction whales bet?
  5. Saves everything to whale_alpha_log.jsonl (one JSON per line)

Usage:
  python whale_alpha_tracker.py              # Run forever alongside main bot
  python whale_alpha_tracker.py --audit      # Just audit existing log, no new tracking
  python whale_alpha_tracker.py --report     # Print full statistical report
"""

import asyncio
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from loguru import logger

# ── Path setup ────────────────────────────────────────────────────────────────
backend_path = os.path.join(os.getcwd(), "backend")
if os.path.exists(backend_path):
    sys.path.append(backend_path)
else:
    sys.path.append(os.getcwd())

load_dotenv(os.path.join(
    backend_path if os.path.exists(backend_path) else os.getcwd(), ".env"
))

from app.core.config import settings
from app.engines.tracker.tracker import SmartMoneyTracker
from app.engines.tracker.cluster_detector import ClusterDetector

# ── Config ────────────────────────────────────────────────────────────────────
LOG_FILE = Path("whale_alpha_log.jsonl")
GAMMA_API = "https://gamma-api.polymarket.com/markets"
CONV_THRESHOLD = 0.65        # Same as main loop
CHECK_INTERVAL_SECONDS = 300  # Check for new signals every 5 minutes
RESOLVE_THRESHOLD_HIGH = 0.97 # Price considered "resolved YES"
RESOLVE_THRESHOLD_LOW  = 0.03 # Price considered "resolved NO"


# ── Log helpers ───────────────────────────────────────────────────────────────

def load_log() -> list[dict]:
    """Load all entries from the JSONL log file."""
    if not LOG_FILE.exists():
        return []
    entries = []
    with open(LOG_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def save_entry(entry: dict):
    """Append a single entry to the JSONL log file."""
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def update_entry(entries: list[dict], market_id: str, updates: dict):
    """Update an existing entry in memory and rewrite the log."""
    for e in entries:
        if e["market_id"] == market_id:
            e.update(updates)
    # Rewrite entire file
    with open(LOG_FILE, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


# ── Market resolution check ───────────────────────────────────────────────────

async def check_resolution(market_id: str, token_id: str) -> dict | None:
    """
    Query Gamma API to check if a market has resolved definitively.
    Returns dict with {resolved: bool, final_price: float, won: bool} or None.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{GAMMA_API}/{market_id}",
                headers={"Accept": "application/json"}
            )
            if resp.status_code != 200:
                return None

            data = resp.json()

            # Try to get current price from tokens
            tokens = data.get("tokens", [])
            price = None
            for token in tokens:
                if token.get("tokenId") == token_id:
                    price = float(token.get("price", 0))
                    break

            # Fallback to top-level price fields
            if price is None:
                price = float(data.get("bestAsk") or data.get("lastTradePrice") or 0)

            if price is None:
                return None

            resolved = price >= RESOLVE_THRESHOLD_HIGH or price <= RESOLVE_THRESHOLD_LOW
            won = price >= RESOLVE_THRESHOLD_HIGH if resolved else None

            return {
                "resolved": resolved,
                "final_price": round(price, 4),
                "won": won,
            }

    except Exception as e:
        logger.debug(f"Resolution check failed for {market_id}: {e}")
        return None


# ── Statistical report ────────────────────────────────────────────────────────

def print_report(entries: list[dict]):
    """Print a full statistical analysis of the whale alpha log."""
    if not entries:
        print("\n📊 Whale Alpha Log is empty. No signals recorded yet.\n")
        return

    total = len(entries)
    resolved = [e for e in entries if e.get("resolved")]
    pending = [e for e in entries if not e.get("resolved")]
    wins = [e for e in resolved if e.get("won") is True]
    losses = [e for e in resolved if e.get("won") is False]

    print("\n" + "=" * 60)
    print("  WHALE ALPHA TRACKER — Statistical Report")
    print("=" * 60)
    print(f"  Total signals recorded : {total}")
    print(f"  Resolved (definitively): {len(resolved)}")
    print(f"  Pending (open)         : {len(pending)}")
    print()

    if resolved:
        accuracy = len(wins) / len(resolved) * 100
        print(f"  Wins   : {len(wins)}")
        print(f"  Losses : {len(losses)}")
        print(f"  Accuracy (raw) : {accuracy:.1f}%")
        print()

        # Statistical significance
        n = len(resolved)
        if n >= 20:
            # Approximate p-value for binomial test (H0: p=0.5)
            # Using normal approximation: z = (wins - n*0.5) / sqrt(n*0.25)
            import math
            z = (len(wins) - n * 0.5) / math.sqrt(n * 0.25)
            # Two-tailed p-value approximation
            p_approx = 2 * (1 - _norm_cdf(abs(z)))
            sig = "✅ SIGNIFICANT" if p_approx < 0.05 else "⚠️  NOT significant"
            print(f"  Statistical test  : z={z:.2f}, p≈{p_approx:.3f} — {sig}")
            print()
        else:
            print(f"  Statistical test  : Need {20 - n} more resolved trades for significance test")
            print()

        # Breakdown by whale_count
        print("  Accuracy by Whale Count:")
        for wc in sorted(set(e.get("whale_count", 0) for e in resolved)):
            subset = [e for e in resolved if e.get("whale_count") == wc]
            subset_wins = sum(1 for e in subset if e.get("won"))
            if subset:
                print(
                    f"    {wc} whale(s): {subset_wins}/{len(subset)} "
                    f"= {subset_wins/len(subset)*100:.1f}%"
                )
        print()

        # Breakdown by entry price bucket
        print("  Accuracy by Entry Price:")
        buckets = [
            (0.0, 0.35,  "0.00-0.35"),
            (0.35, 0.50, "0.35-0.50"),
            (0.50, 0.65, "0.50-0.65"),
            (0.65, 1.0,  "0.65-1.00"),
        ]
        for lo, hi, label in buckets:
            subset = [
                e for e in resolved
                if lo <= e.get("entry_price", 0) < hi
            ]
            if subset:
                subset_wins = sum(1 for e in subset if e.get("won"))
                print(
                    f"    {label}: {subset_wins}/{len(subset)} "
                    f"= {subset_wins/len(subset)*100:.1f}%"
                )
        print()

    # Recent signals
    print("  Last 10 signals:")
    print(f"  {'Market':<40} {'Entry':>6} {'Whales':>6} {'Status':<12}")
    print("  " + "-" * 68)
    for e in sorted(entries, key=lambda x: x["detected_at"], reverse=True)[:10]:
        status = "PENDING"
        if e.get("resolved"):
            status = "WIN ✅" if e.get("won") else "LOSS ❌"
        question = e.get("market_question", "?")[:38]
        print(
            f"  {question:<40} "
            f"{e.get('entry_price', 0):>6.3f} "
            f"{e.get('whale_count', 0):>6} "
            f"{status:<12}"
        )
    print("=" * 60 + "\n")


def _norm_cdf(x: float) -> float:
    """Approximate CDF of standard normal distribution."""
    import math
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


# ── Resolution audit ──────────────────────────────────────────────────────────

async def audit_pending(entries: list[dict]) -> int:
    """
    Check all pending entries and update their resolution status.
    Returns number of newly resolved entries.
    """
    pending = [e for e in entries if not e.get("resolved")]
    if not pending:
        logger.info("Audit: No pending entries to check.")
        return 0

    logger.info(f"Audit: Checking {len(pending)} pending signals...")
    newly_resolved = 0

    for entry in pending:
        result = await check_resolution(
            entry["market_id"], entry.get("token_id", "")
        )
        if result and result["resolved"]:
            entry["resolved"] = True
            entry["final_price"] = result["final_price"]
            entry["won"] = result["won"]
            entry["resolved_at"] = datetime.now(timezone.utc).isoformat()
            newly_resolved += 1
            status = "WIN ✅" if result["won"] else "LOSS ❌"
            logger.success(
                f"Resolved: {entry['market_question'][:50]} → "
                f"{status} (price={result['final_price']})"
            )
        await asyncio.sleep(0.3)  # Rate limit

    if newly_resolved > 0:
        update_entry(entries, None, {})  # Trigger rewrite
        # Actually rewrite entire file
        with open(LOG_FILE, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
        logger.info(f"Audit: {newly_resolved} new resolutions recorded.")
    else:
        logger.info("Audit: No new resolutions found.")

    return newly_resolved


# ── Main tracking loop ────────────────────────────────────────────────────────

async def tracking_loop():
    """
    Main loop: detect whale signals and record them for alpha measurement.
    Runs every CHECK_INTERVAL_SECONDS seconds.
    """
    logger.info("=" * 60)
    logger.info("  WHALE ALPHA TRACKER — Parallel Mode")
    logger.info("  Measuring raw signal value WITHOUT Council AI")
    logger.info(f"  Log file: {LOG_FILE.absolute()}")
    logger.info("=" * 60)

    tracker = SmartMoneyTracker()
    detector = ClusterDetector(min_wallets=settings.AUTONOMOUS_MIN_WALLETS or 2)

    # Load existing log
    entries = load_log()
    logger.info(f"Loaded {len(entries)} existing entries from log.")

    cycle = 0
    while True:
        try:
            logger.info(f"--- Alpha Tracker Cycle {cycle} ---")

            # ── Detect whale signals ──────────────────────────────────────────
            whale_alerts = await detector.scan_for_clusters()
            high_conv = [
                a for a in whale_alerts if a.confidence >= CONV_THRESHOLD
            ]

            new_signals = 0
            for alert in high_conv:
                # Skip if already logged (deduplication by market_id)
                already_logged = any(
                    e["market_id"] == alert.market_id for e in entries
                )
                if already_logged:
                    continue

                entry = {
                    "market_id": alert.market_id,
                    "market_question": alert.market_question,
                    "token_id": alert.token_id,
                    "outcome": alert.outcome,
                    "entry_price": None,  # Will try to get from CLOB
                    "whale_count": alert.wallet_count,
                    "confidence": alert.confidence,
                    "end_date": alert.end_date,
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                    "resolved": False,
                    "final_price": None,
                    "won": None,
                    "resolved_at": None,
                    "source": "WHALE_TRACKER_RAW",  # Distinct from main bot logs
                }

                # Try to get entry price from CLOB
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        resp = await client.get(
                            f"https://clob.polymarket.com/books",
                            params={"token_id": alert.token_id},
                            headers={"Accept": "application/json"}
                        )
                        if resp.status_code == 200:
                            book = resp.json()
                            asks = book.get("asks", [])
                            if asks:
                                best_ask = float(asks[0].get("price", 0))
                                entry["entry_price"] = best_ask
                except Exception:
                    pass  # Entry price stays None — still valuable signal data

                save_entry(entry)
                entries.append(entry)
                new_signals += 1

                logger.success(
                    f"[ALPHA] New signal: {alert.market_question[:50]} | "
                    f"Price: {entry['entry_price']} | "
                    f"Whales: {alert.wallet_count} | "
                    f"Conf: {alert.confidence:.2f}"
                )

            if new_signals > 0:
                logger.info(f"Alpha Tracker: {new_signals} new signals recorded.")
            else:
                logger.info("Alpha Tracker: No new whale signals this cycle.")

            # ── Audit pending resolutions every 5 cycles ──────────────────────
            if cycle % 5 == 0 and cycle > 0:
                newly_resolved = await audit_pending(entries)
                if newly_resolved > 0:
                    print_report(entries)

            # ── Print report every 50 cycles ─────────────────────────────────
            if cycle % 50 == 0 and cycle > 0:
                print_report(entries)

            cycle += 1
            logger.info(f"Alpha Tracker sleeping {CHECK_INTERVAL_SECONDS}s...")
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.warning("Alpha Tracker stopped by user.")
            print_report(entries)
            break
        except Exception as e:
            logger.error(f"Alpha Tracker error: {e}")
            await asyncio.sleep(60)


# ── Entry point ───────────────────────────────────────────────────────────────

async def main(audit_only: bool = False, report_only: bool = False):
    entries = load_log()

    if report_only:
        print_report(entries)
        return

    if audit_only:
        await audit_pending(entries)
        print_report(entries)
        return

    await tracking_loop()


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            import sys
            import io
            if isinstance(sys.stdout, io.TextIOWrapper):
                sys.stdout.reconfigure(encoding='utf-8')
        except (AttributeError, ImportError):
            pass

    parser = argparse.ArgumentParser(
        description="PolyMaster Whale Alpha Tracker — measures raw signal value"
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Audit existing log for new resolutions, then exit"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print statistical report from existing log, then exit"
    )
    args = parser.parse_args()

    asyncio.run(main(audit_only=args.audit, report_only=args.report))
