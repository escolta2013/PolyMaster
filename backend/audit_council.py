"""
Council Accuracy Auditor — Post-hoc verification of WOULD_EXECUTE decisions.

Parses the autonomous.log for all WOULD_EXECUTE entries, resolves each market
against Polymarket's Gamma API to check real outcomes, and produces a segmented
accuracy report broken down by:
  1. Edge Net bucket (0.03-0.07, 0.07-0.12, >0.12)
  2. Market category (Sports, Politics, Crypto, Other)
  3. Overall win rate

Usage:
    python audit_council.py
"""

import asyncio
import re
import httpx
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple


def safe_parse_outcome_prices(raw) -> Tuple[Optional[float], Optional[float]]:
    """Parse outcomePrices which can be a JSON string, list, or None."""
    if raw is None:
        return None, None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None, None
    if isinstance(raw, list) and len(raw) >= 2:
        try:
            return float(raw[0]), float(raw[1])
        except (ValueError, TypeError):
            return None, None
    return None, None

# ── Constants ────────────────────────────────────────────────
LOG_PATH = Path(__file__).parent / "logs" / "autonomous.log"
GAMMA_API = "https://gamma-api.polymarket.com"

# Regex patterns
# Pattern 1: The decision line with metrics
EXEC_PATTERN = re.compile(
    r"\[PAPER\] WOULD_EXECUTE \| "
    r"Market: (?P<market>.+?) \| "
    r"Council: (?P<council>[\d.]+) \| "
    r"Ask: (?P<ask>[\d.]+) \| "
    r"Spread: (?P<spread>[\d.]+) \| "
    r"Edge Brute: (?P<edge_brute>[+\-][\d.]+) \| "
    r"Edge Net: (?P<edge_net>[+\-][\d.]+) \| "
    r"Agents: (?P<agents>\{.+\})"
)
# Pattern 2: The follow-up line with market_id
LOGGED_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+).*"
    r"\[PAPER\] Logged WOULD_EXECUTE for (?P<market_id>\d+)"
)

# Category keywords for classification
SPORTS_KW = [
    "vs.", "o/u", "spread:", "nba", "nfl", "mlb", "nhl", "ufc",
    "win on 2026", "mavericks", "thunder", "lakers", "celtics",
    "bucks", "raptors", "warriors", "cavaliers", "hawks", "bulls",
    "heat", "nets", "pacers", "hornets", "magic", "suns", "pelicans",
    "real sociedad", "galatasaray", "crvena zvezda", "fútbol",
    "fk ", "psg", "liga", "ligue", "serie a", "premier league",
    "rebounds", "assists", "points", "handicap", "oliveira",
    "holloway", "predators", "blackhawks", "mackinnon", "flagg",
    "holmgren", "fight", "bout"
]
POLITICS_KW = [
    "trump", "biden", "republican", "democrat", "governor", "senate",
    "congress", "election", "impeach", "ipo", "fed ", "interest rate",
    "israel", "russia", "ukraine", "yemen", "abraham accords",
    "putin", "zelensky", "dhs", "shutdown", "mcconnell", "musk post",
    "state of the union", "nato", "invade", "strike", "maduro",
    "prime minister", "president", "accords", "afd", "united russia",
    "stratton", "hale", "taliban", "newsom", "desantis", "pence"
]
CRYPTO_KW = [
    "bitcoin", "ethereum", "solana", "xrp", "bnb", "crypto",
    "token", "fdv", "ipo", "dip to", "reach $", "above $",
    "zcash", "megaeth", "metamask", "perplexity", "discord",
    "lighter", "predict.fun", "solstice", "fabric", "usd.ai",
    "pacifica", "vanta", "backpack", "meteora", "hyperliquid",
    "loopscale"
]


@dataclass
class TradeRecord:
    """A single WOULD_EXECUTE decision with its verification status."""
    market_id: str
    market_name: str
    council_score: float
    ask_price: float
    spread: float
    edge_brute: float
    edge_net: float
    agents: str
    timestamp: str = ""
    
    # Resolution data (filled after Gamma API check)
    resolved: Optional[bool] = None
    outcome: Optional[str] = None       # "YES" or "NO" or None
    resolution_price: Optional[float] = None  # 1.0 if YES won, 0.0 if NO won
    council_correct: Optional[bool] = None
    category: str = "Other"
    
    @property
    def edge_bucket(self) -> str:
        en = abs(self.edge_net)
        if en < 0.07:
            return "0.03-0.07"
        elif en < 0.12:
            return "0.07-0.12"
        else:
            return ">0.12"


def classify_market(name: str) -> str:
    """Classify a market into a category based on keywords."""
    low = name.lower()
    
    # Sports first (most distinctive)
    if any(kw in low for kw in SPORTS_KW):
        return "Sports"
    
    # Crypto/Tech
    if any(kw in low for kw in CRYPTO_KW):
        return "Crypto/Tech"
    
    # Politics/Geopolitics
    if any(kw in low for kw in POLITICS_KW):
        return "Politics"
    
    return "Other"


def parse_log() -> List[TradeRecord]:
    """Parse the autonomous.log and extract all WOULD_EXECUTE entries."""
    print(f"📄 Reading log file: {LOG_PATH}")
    
    lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"   Total lines: {len(lines):,}")
    
    # First pass: find all WOULD_EXECUTE decision lines
    exec_entries = []
    for i, line in enumerate(lines):
        m = EXEC_PATTERN.search(line)
        if m:
            exec_entries.append({
                "line_idx": i,
                "market": m.group("market"),
                "council": float(m.group("council")),
                "ask": float(m.group("ask")),
                "spread": float(m.group("spread")),
                "edge_brute": float(m.group("edge_brute")),
                "edge_net": float(m.group("edge_net")),
                "agents": m.group("agents"),
            })

    print(f"   Found {len(exec_entries)} WOULD_EXECUTE decision lines")

    # Second pass: match each decision line to its "Logged WOULD_EXECUTE for XXXX" line
    # The logged line always comes 1-3 lines after the decision line
    trades: List[TradeRecord] = []
    seen_market_ids = set()
    
    for entry in exec_entries:
        start = entry["line_idx"] + 1
        end = min(start + 5, len(lines))
        market_id = None
        timestamp = ""
        
        for j in range(start, end):
            lm = LOGGED_PATTERN.search(lines[j])
            if lm:
                market_id = lm.group("market_id")
                timestamp = lm.group("timestamp")
                break
        
        if not market_id:
            continue
        
        # Deduplicate: only keep the FIRST occurrence of each market_id
        # (the cache means the same market gets re-evaluated each cycle)
        if market_id in seen_market_ids:
            continue
        seen_market_ids.add(market_id)
            
        trade = TradeRecord(
            market_id=market_id,
            market_name=entry["market"],
            council_score=entry["council"],
            ask_price=entry["ask"],
            spread=entry["spread"],
            edge_brute=entry["edge_brute"],
            edge_net=entry["edge_net"],
            agents=entry["agents"],
            timestamp=timestamp,
            category=classify_market(entry["market"]),
        )
        trades.append(trade)
    
    print(f"   Unique markets after dedup: {len(trades)}")
    return trades


async def check_resolution(client: httpx.AsyncClient, trade: TradeRecord) -> TradeRecord:
    """
    Check if a market has effectively resolved by querying the Gamma API.
    
    Resolution detection strategy:
    - Polymarket doesn't always set `closed=True` immediately. Sports events
      can take hours for the UMA oracle to formally resolve.
    - However, `outcomePrices` converge to 0.0/1.0 once the result is known.
    - We use outcomePrices as the primary signal:
        outcomePrices[0] > 0.95 → first outcome won (YES / first team)
        outcomePrices[0] < 0.05 → second outcome won (NO / second team)
    
    The bot always buys the first token (YES / first team) at the ask price.
    So: council_correct = True when the first outcome price → 1.0.
    """
    try:
        resp = await client.get(
            f"{GAMMA_API}/markets/{trade.market_id}",
            timeout=10.0
        )
        
        if resp.status_code == 404:
            trade.resolved = None
            return trade
            
        resp.raise_for_status()
        data = resp.json()
        
        # Core resolution fields
        is_closed = data.get("closed", False)
        outcome_field = data.get("outcome")     # Formal UMA resolution (often None)
        outcome_prices_raw = data.get("outcomePrices")  # e.g. ["0.9995", "0.0005"]
        outcomes = data.get("outcomes", [])      # e.g. ["Thunder", "Raptors"] or ["Yes", "No"]
        end_date_str = data.get("endDate", "")
        uma_status = data.get("umaResolutionStatus", "")
        
        # Parse outcomePrices safely (Gamma API returns JSON string!)
        first_price, second_price = safe_parse_outcome_prices(outcome_prices_raw)
        
        # ── Strategy 1: Formal resolution (closed=True + outcome field) ──
        if is_closed and outcome_field is not None:
            trade.resolved = True
            outcome_str = str(outcome_field).strip().upper()
            if outcome_str in ("YES", "1", "TRUE"):
                trade.outcome = "YES"
                trade.council_correct = True
            elif outcome_str in ("NO", "0", "FALSE"):
                trade.outcome = "NO"
                trade.council_correct = False
            else:
                # Outcome matches first or second outcome name
                if outcomes and outcome_str == str(outcomes[0]).strip().upper():
                    trade.outcome = "YES"
                    trade.council_correct = True
                elif outcomes and len(outcomes) > 1 and outcome_str == str(outcomes[1]).strip().upper():
                    trade.outcome = "NO"
                    trade.council_correct = False
                else:
                    trade.resolved = None
            return trade
        
        # ── Strategy 2: outcomePrices convergence (de facto resolution) ──
        # If price is >0.95 or <0.05, the market has effectively resolved
        # even if UMA hasn't formally closed it yet
        if first_price is not None:
            if first_price >= 0.95:
                trade.resolved = True
                trade.outcome = "YES"
                trade.resolution_price = first_price
                trade.council_correct = True  # Bot bought first token, it won
                return trade
            elif first_price <= 0.05:
                trade.resolved = True
                trade.outcome = "NO"
                trade.resolution_price = first_price
                trade.council_correct = False  # Bot bought first token, it lost
                return trade
        
        # ── Strategy 3: UMA proposed but price hasn't moved (edge case) ──
        if uma_status == "proposed" and first_price is not None:
            if first_price >= 0.90:
                trade.resolved = True
                trade.outcome = "YES"
                trade.council_correct = True
                return trade
            elif first_price <= 0.10:
                trade.resolved = True
                trade.outcome = "NO"
                trade.council_correct = False
                return trade
        
        # ── Not resolved yet ──
        trade.resolved = False
        return trade
        
    except Exception as e:
        # Don't crash the whole audit on one failure
        return trade


async def run_audit(trades: List[TradeRecord]) -> List[TradeRecord]:
    """Check resolution status for all trades via Gamma API."""
    print(f"\n🔍 Checking resolution status for {len(trades)} unique markets...")
    
    # Use semaphore to limit concurrent requests
    sem = asyncio.Semaphore(10)
    
    async def bounded_check(client, trade):
        async with sem:
            return await check_resolution(client, trade)
    
    async with httpx.AsyncClient() as client:
        tasks = [bounded_check(client, t) for t in trades]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    verified = []
    errors = 0
    for r in results:
        if isinstance(r, Exception):
            errors += 1
        else:
            verified.append(r)
    
    if errors:
        print(f"   ⚠️  {errors} API errors encountered")
    
    return verified


def generate_report(trades: List[TradeRecord]):
    """Generate the full accuracy report."""
    
    resolved = [t for t in trades if t.resolved is True]
    unresolved = [t for t in trades if t.resolved is False]
    unknown = [t for t in trades if t.resolved is None]
    
    print("\n" + "=" * 80)
    print("   📊 COUNCIL ACCURACY AUDIT REPORT")
    print("   " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)
    
    # ── Section 1: Overview ──────────────────────────────────
    print(f"\n📋 OVERVIEW")
    print(f"   Total unique WOULD_EXECUTE markets: {len(trades)}")
    print(f"   ✅ Resolved (verifiable):            {len(resolved)}")
    print(f"   ⏳ Unresolved (still open):           {len(unresolved)}")
    print(f"   ❓ Unknown/Error:                     {len(unknown)}")
    
    if not resolved:
        print("\n⚠️  No resolved markets found. Cannot compute accuracy.")
        print("    This is expected if all markets are long-term (politics, crypto).")
        print("    Sports markets typically resolve same-day.")
        return
    
    # ── Section 2: Overall Accuracy ─────────────────────────
    wins = [t for t in resolved if t.council_correct]
    losses = [t for t in resolved if not t.council_correct]
    accuracy = len(wins) / len(resolved) * 100
    
    print(f"\n🎯 OVERALL ACCURACY")
    print(f"   Wins: {len(wins)} | Losses: {len(losses)} | Total: {len(resolved)}")
    print(f"   ✅ Accuracy: {accuracy:.1f}%")
    
    # Simulated P&L (assume $10 per trade at the ask price)
    total_pnl = 0.0
    for t in resolved:
        if t.council_correct:
            # Won: payout is $10 * (1.0 / ask_price) - $10
            pnl = 10.0 * (1.0 / t.ask_price) - 10.0
        else:
            # Lost: lose the $10
            pnl = -10.0
        total_pnl += pnl
    
    avg_edge = sum(t.edge_net for t in resolved) / len(resolved)
    print(f"   📈 Simulated P&L ($10/trade): ${total_pnl:+.2f}")
    print(f"   📐 Average Edge Net: {avg_edge:+.4f}")
    
    # ── Section 3: Accuracy by Edge Net Bucket ──────────────
    print(f"\n📏 ACCURACY BY EDGE NET BUCKET")
    print(f"   {'Bucket':<15} {'Wins':<6} {'Losses':<8} {'Total':<7} {'Accuracy':<10} {'Avg Edge':<10} {'Sim P&L':<10}")
    print(f"   {'-'*13}   {'-'*4}   {'-'*6}   {'-'*5}   {'-'*8}   {'-'*8}   {'-'*8}")
    
    buckets = defaultdict(list)
    for t in resolved:
        buckets[t.edge_bucket].append(t)
    
    for bucket in ["0.03-0.07", "0.07-0.12", ">0.12"]:
        group = buckets.get(bucket, [])
        if not group:
            print(f"   {bucket:<15} {'—':<6} {'—':<8} {0:<7} {'N/A':<10} {'N/A':<10} {'N/A':<10}")
            continue
        
        w = sum(1 for t in group if t.council_correct)
        l = len(group) - w
        acc = w / len(group) * 100
        avg_e = sum(t.edge_net for t in group) / len(group)
        
        sim_pnl = 0.0
        for t in group:
            if t.council_correct:
                sim_pnl += 10.0 * (1.0 / t.ask_price) - 10.0
            else:
                sim_pnl -= 10.0
        
        print(f"   {bucket:<15} {w:<6} {l:<8} {len(group):<7} {acc:<9.1f}% {avg_e:<+9.4f}  ${sim_pnl:<+9.2f}")
    
    # ── Section 4: Accuracy by Market Category ──────────────
    print(f"\n🏷️  ACCURACY BY MARKET CATEGORY")
    print(f"   {'Category':<15} {'Wins':<6} {'Losses':<8} {'Total':<7} {'Accuracy':<10} {'Avg Edge':<10}")
    print(f"   {'-'*13}   {'-'*4}   {'-'*6}   {'-'*5}   {'-'*8}   {'-'*8}")
    
    categories = defaultdict(list)
    for t in resolved:
        categories[t.category].append(t)
    
    for cat in sorted(categories.keys()):
        group = categories[cat]
        w = sum(1 for t in group if t.council_correct)
        l = len(group) - w
        acc = w / len(group) * 100
        avg_e = sum(t.edge_net for t in group) / len(group)
        print(f"   {cat:<15} {w:<6} {l:<8} {len(group):<7} {acc:<9.1f}% {avg_e:<+9.4f}")
    
    # ── Section 5: Top Wins & Worst Losses ──────────────────
    print(f"\n🏆 TOP 10 WINS (Highest Edge Net)")
    wins_sorted = sorted(wins, key=lambda t: t.edge_net, reverse=True)[:10]
    for i, t in enumerate(wins_sorted, 1):
        print(f"   {i:>2}. [{t.category:<10}] Edge: {t.edge_net:+.3f} | Ask: {t.ask_price:.2f} | Council: {t.council_score:.3f} | {t.market_name[:60]}")
    
    print(f"\n💀 TOP 10 LOSSES (Highest Edge Net that was wrong)")
    losses_sorted = sorted(losses, key=lambda t: t.edge_net, reverse=True)[:10]
    for i, t in enumerate(losses_sorted, 1):
        print(f"   {i:>2}. [{t.category:<10}] Edge: {t.edge_net:+.3f} | Ask: {t.ask_price:.2f} | Council: {t.council_score:.3f} | {t.market_name[:60]}")
    
    # ── Section 6: Production Filter Simulation ─────────────
    print(f"\n🏭 PRODUCTION FILTER SIMULATION (Spread ≤ 0.15)")
    prod_trades = [t for t in resolved if t.spread <= 0.15]
    if prod_trades:
        prod_wins = sum(1 for t in prod_trades if t.council_correct)
        prod_acc = prod_wins / len(prod_trades) * 100
        prod_pnl = 0.0
        for t in prod_trades:
            if t.council_correct:
                prod_pnl += 10.0 * (1.0 / t.ask_price) - 10.0
            else:
                prod_pnl -= 10.0
        
        print(f"   Trades surviving 0.15 spread filter: {len(prod_trades)}/{len(resolved)}")
        print(f"   Accuracy with production filter: {prod_acc:.1f}%")
        print(f"   Simulated P&L ($10/trade): ${prod_pnl:+.2f}")
    else:
        print(f"   No trades would survive the 0.15 spread filter.")
    
    # ── Section 7: Strict Production Simulation ─────────────
    print(f"\n🔒 STRICT PRODUCTION SIMULATION (Spread ≤ 0.05, Edge > 0.05)")
    strict = [t for t in resolved if t.spread <= 0.05 and t.edge_net > 0.05]
    if strict:
        s_wins = sum(1 for t in strict if t.council_correct)
        s_acc = s_wins / len(strict) * 100
        s_pnl = 0.0
        for t in strict:
            if t.council_correct:
                s_pnl += 10.0 * (1.0 / t.ask_price) - 10.0
            else:
                s_pnl -= 10.0
        print(f"   Trades surviving strict filter: {len(strict)}/{len(resolved)}")
        print(f"   Accuracy: {s_acc:.1f}%")
        print(f"   Simulated P&L ($10/trade): ${s_pnl:+.2f}")
    else:
        print(f"   No trades would survive the strict filter.")
    
    # ── Section 8: Unresolved Markets Summary ───────────────
    print(f"\n⏳ UNRESOLVED MARKETS BY CATEGORY (still open)")
    unr_cats = defaultdict(int)
    for t in unresolved:
        unr_cats[t.category] += 1
    for cat in sorted(unr_cats.keys()):
        print(f"   {cat}: {unr_cats[cat]}")
    
    print(f"\n{'=' * 80}")
    print(f"   Audit complete. {len(resolved)} markets verified out of {len(trades)} total.")
    print(f"{'=' * 80}")


async def main():
    # Step 1: Parse the log
    trades = parse_log()
    
    if not trades:
        print("❌ No WOULD_EXECUTE entries found in the log.")
        return
    
    # Category breakdown before API calls
    cat_counts = defaultdict(int)
    for t in trades:
        cat_counts[t.category] += 1
    print(f"\n📊 Category distribution:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count}")
    
    # Step 2: Check resolutions via Gamma API
    trades = await run_audit(trades)
    
    # Step 3: Generate the report
    generate_report(trades)


if __name__ == "__main__":
    asyncio.run(main())
