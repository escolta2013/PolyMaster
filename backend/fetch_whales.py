import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, asdict
from typing import Optional

import httpx

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
LEADERBOARD_URL = "https://data-api.polymarket.com/v1/leaderboard"
ACTIVITY_URL    = "https://data-api.polymarket.com/v1/activity"  # per-wallet activity
GAMMA_URL       = "https://gamma-api.polymarket.com"

DEFAULT_WINDOW    = "30d"    # Time window: 1d, 7d, 30d, all
DEFAULT_MIN_PNL   = 10_000   # Minimum USD profit
DEFAULT_MIN_TRADES = 50      # Minimum number of resolved trades
DEFAULT_MIN_WIN_RATE = 0.55  # Minimum win rate (55%)
DEFAULT_TOP_N     = 100      # Fetch top N from leaderboard
TARGET_WALLETS    = 30       # Final wallet count to keep

HEADERS = {
    "User-Agent": "PolyMaster-WhaleFetcher/1.0",
    "Accept": "application/json",
}

# ─────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────
@dataclass
class WhaleCandidate:
    address: str
    username: str
    pnl: float
    volume: float
    win_rate: Optional[float] = None
    total_trades: Optional[int] = None
    grade: str = "WHALE"
    verified: bool = False
    valid: bool = True
    reject_reason: str = ""

# ─────────────────────────────────────────────
# Fetching
# ─────────────────────────────────────────────
async def fetch_leaderboard(
    window: str = DEFAULT_WINDOW,
    top_n: int = DEFAULT_TOP_N
) -> list[dict]:
    """Fetch top traders from Polymarket Data API leaderboard."""
    print(f"\n📡 Fetching top {top_n} traders (window={window})...")
    
    params = {
        "window": window,
        "limit": top_n,
        "sortBy": "pnl",
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(LEADERBOARD_URL, params=params, headers=HEADERS)
            resp.raise_for_status()
            data = resp.json()
            
            # Handle both list and dict responses
            if isinstance(data, list):
                traders = data
            elif isinstance(data, dict):
                traders = data.get("data", data.get("traders", []))
            else:
                traders = []
            
            print(f"   ✅ Fetched {len(traders)} traders from leaderboard")
            return traders
            
        except httpx.HTTPStatusError as e:
            print(f"   ❌ HTTP error {e.response.status_code}: {e.response.text[:200]}")
            return []
        except Exception as e:
            print(f"   ❌ Error fetching leaderboard: {e}")
            return []


async def fetch_wallet_activity(
    wallet: str,
    client: httpx.AsyncClient,
    limit: int = 200
) -> dict:
    """Fetch recent activity for a wallet to calculate win rate."""
    try:
        params = {
            "user": wallet,
            "limit": limit,
            "offset": 0,
        }
        resp = await client.get(ACTIVITY_URL, params=params, headers=HEADERS)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def calculate_win_rate(activity_data: dict) -> tuple[Optional[float], int]:
    """
    Calculate win rate from wallet activity.
    Returns (win_rate, total_resolved_trades).
    """
    if not activity_data:
        return None, 0
    
    # Activity can be a list or dict with data key
    if isinstance(activity_data, list):
        trades = activity_data
    elif isinstance(activity_data, dict):
        trades = activity_data.get("data", activity_data.get("history", []))
    else:
        return None, 0
    
    wins = 0
    losses = 0
    
    for trade in trades:
        # Look for resolved trade indicators
        # Polymarket activity uses various field names
        outcome = (
            trade.get("outcome") or
            trade.get("resolution") or
            trade.get("result") or
            ""
        )
        if isinstance(outcome, str):
            outcome = outcome.upper()
        
        pnl_val = trade.get("pnl") or trade.get("profit") or 0
        try:
            pnl = float(pnl_val)
        except:
            pnl = 0.0
            
        if outcome in ("YES", "WIN", "WON", "RESOLVED_YES") or pnl > 0:
            wins += 1
        elif outcome in ("NO", "LOSS", "LOST", "RESOLVED_NO") or pnl < 0:
            losses += 1
    
    total = wins + losses
    if total == 0:
        return None, 0
    
    return wins / total, total


async def validate_wallet(
    candidate: WhaleCandidate,
    client: httpx.AsyncClient,
    min_trades: int,
    min_win_rate: float,
) -> WhaleCandidate:
    """Fetch activity and validate a wallet candidate."""
    
    # Validate address format (EVM)
    if not candidate.address.startswith("0x") or len(candidate.address) != 42:
        candidate.valid = False
        candidate.reject_reason = f"Invalid address format: {candidate.address}"
        return candidate
    
    # Fetch activity
    activity = await fetch_wallet_activity(candidate.address, client)
    win_rate, total_trades = calculate_win_rate(activity)
    
    candidate.win_rate = win_rate
    candidate.total_trades = total_trades
    
    # Filter: minimum trades
    if total_trades < min_trades:
        candidate.valid = False
        candidate.reject_reason = f"Too few trades: {total_trades} < {min_trades}"
        return candidate
    
    # Filter: minimum win rate (if we have data)
    if win_rate is not None and win_rate < min_win_rate:
        candidate.valid = False
        candidate.reject_reason = f"Low win rate: {win_rate:.1%} < {min_win_rate:.1%}"
        return candidate
    
    # Assign grade based on PnL
    if candidate.pnl >= 100_000:
        candidate.grade = "WHALE"
    elif candidate.pnl >= 25_000:
        candidate.grade = "SHARK"
    else:
        candidate.grade = "ORCA"
    
    return candidate


# ─────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────
async def main(
    window: str = DEFAULT_WINDOW,
    min_pnl: float = DEFAULT_MIN_PNL,
    min_trades: int = DEFAULT_MIN_TRADES,
    min_win_rate: float = DEFAULT_MIN_WIN_RATE,
    top_n: int = DEFAULT_TOP_N,
    output: Optional[str] = None,
    dry_run: bool = False,
):
    print("=" * 60)
    print("  PolyMaster Whale Tracker — Wallet Fetcher")
    print("=" * 60)
    print(f"  Window:       {window}")
    print(f"  Min PnL:      ${min_pnl:,.0f}")
    print(f"  Min Trades:   {min_trades}")
    print(f"  Min Win Rate: {min_win_rate:.0%}")
    print("=" * 60)
    
    # Step 1: Fetch leaderboard
    traders = await fetch_leaderboard(window, top_n)
    
    if not traders:
        print("\n❌ No traders fetched. Check API connectivity.")
        sys.exit(1)
    
    # Step 2: Parse into candidates, filter by PnL
    candidates = []
    for t in traders:
        address = (
            t.get("proxyWallet") or
            t.get("address") or
            t.get("wallet") or ""
        ).strip().lower()
        
        pnl = float(t.get("pnl") or t.get("profit") or 0)
        vol = float(t.get("vol") or t.get("volume") or 0)
        username = t.get("userName") or t.get("username") or address[:8]
        verified = t.get("verifiedBadge", False)
        
        if not address:
            continue
            
        if pnl < min_pnl:
            continue
        
        c = WhaleCandidate(
            address=address,
            username=username,
            pnl=pnl,
            volume=vol,
            verified=verified,
        )
        if c.pnl >= 100_000:
            c.grade = "WHALE"
        elif c.pnl >= 25_000:
            c.grade = "SHARK"
        else:
            c.grade = "ORCA"
        candidates.append(c)
    
    print(f"\n🔍 {len(candidates)} candidates pass PnL filter (>${min_pnl:,.0f})")
    
    if not candidates:
        print("   Try lowering --min-pnl")
        sys.exit(1)
    
    # Step 3: Validate each wallet (activity + win rate)
    if dry_run:
        print("\n⚡ Dry run — skipping activity validation")
        valid_wallets = [c for c in candidates[:TARGET_WALLETS]]
    else:
        print(f"\n🔎 Validating {len(candidates)} candidates (fetching activity)...")
        print("   This may take 30-60 seconds...\n")
        
        async with httpx.AsyncClient(timeout=20) as client:
            # Process in batches to avoid rate limiting
            batch_size = 10
            validated = []
            
            for i in range(0, len(candidates), batch_size):
                batch = candidates[i:i + batch_size]
                tasks = [
                    validate_wallet(c, client, min_trades, min_win_rate)
                    for c in batch
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for r in results:
                    if isinstance(r, Exception):
                        continue
                    validated.append(r)
                
                # Rate limiting: pause between batches
                if i + batch_size < len(candidates):
                    await asyncio.sleep(1)
                
                valid_count = sum(1 for c in validated if c.valid)
                print(f"   Processed {min(i+batch_size, len(candidates))}/{len(candidates)} | Valid so far: {valid_count}")
        
        valid_wallets = [c for c in validated if c.valid]
    
    # Step 4: Sort by PnL and take top TARGET_WALLETS
    valid_wallets.sort(key=lambda x: x.pnl, reverse=True)
    final_wallets = valid_wallets[:TARGET_WALLETS]
    
    # Step 5: Report results
    print(f"\n{'=' * 60}")
    print(f"  ✅ VALIDATED WALLETS: {len(final_wallets)}")
    print(f"{'=' * 60}")
    
    if not final_wallets:
        print("\n⚠️  No wallets passed all filters.")
        print("   Suggestions:")
        print(f"   - Lower --min-trades (currently {min_trades})")
        print(f"   - Lower --min-win-rate (currently {min_win_rate:.0%})")
        print(f"   - Lower --min-pnl (currently ${min_pnl:,.0f})")
        sys.exit(1)
    
    print(f"\n{'Grade':<8} {'PnL':>12} {'WinRate':>9} {'Trades':>8}  {'Username':<20}  Address")
    print("-" * 90)
    
    for w in final_wallets:
        win_str = f"{w.win_rate:.1%}" if w.win_rate is not None else "N/A"
        trades_str = str(w.total_trades) if w.total_trades else "N/A"
        verified_badge = "✓" if w.verified else " "
        print(
            f"{w.grade:<8} ${w.pnl:>11,.0f} {win_str:>9} {trades_str:>8}"
            f"  {w.username[:20]:<20}{verified_badge} {w.address}"
        )
    
    # Step 6: Generate tracker.py format
    print(f"\n{'=' * 60}")
    print("  📋 COPY THIS INTO tracker.py → SMART_MONEY_WALLETS")
    print(f"{'=' * 60}\n")
    
    wallet_list = []
    for w in final_wallets:
        wallet_list.append({
            "address": w.address,
            "grade": w.grade,
            "username": w.username,
            "pnl_usd": round(w.pnl, 2),
            "win_rate": round(w.win_rate, 3) if w.win_rate else None,
            "source": f"leaderboard_{window}",
            "fetched_at": time.strftime("%Y-%m-%d"),
        })
    
    print("SMART_MONEY_WALLETS = [")
    for w in wallet_list:
        grade = w['grade']
        addr = w['address']
        user = w['username']
        pnl = w['pnl_usd']
        wr = f"{w['win_rate']:.1%}" if w['win_rate'] else 'N/A'
        print(f'    "{addr}",  # {grade} | {user} | PnL: ${pnl:,.0f} | WR: {wr}')
    print("]")
    
    # Step 7: Save to file if requested
    if output:
        with open(output, "w") as f:
            json.dump(wallet_list, f, indent=2)
        print(f"\n💾 Saved {len(wallet_list)} wallets to {output}")
    
    # Step 8: Rejected candidates summary
    if not dry_run and len(candidates) > len(final_wallets):
        rejected = [c for c in validated if not c.valid]
        if rejected:
            print(f"\n⚠️  Rejected {len(rejected)} candidates:")
            reasons = {}
            for r in rejected:
                key = r.reject_reason.split(":")[0]
                reasons[key] = reasons.get(key, 0) + 1
            for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
                print(f"   - {reason}: {count}")
    
    print(f"\n✅ Done. Add the {len(final_wallets)} addresses above to SMART_MONEY_WALLETS in tracker.py")
    print("   Then restart the bot to activate the Whale Tracker.\n")
    
    return wallet_list


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch top Polymarket traders for PolyMaster Whale Tracker"
    )
    parser.add_argument(
        "--window",
        default=DEFAULT_WINDOW,
        choices=["1d", "7d", "30d", "all"],
        help="Leaderboard time window (default: 30d)"
    )
    parser.add_argument(
        "--min-pnl",
        type=float,
        default=DEFAULT_MIN_PNL,
        help=f"Minimum PnL in USD (default: {DEFAULT_MIN_PNL:,})"
    )
    parser.add_argument(
        "--min-trades",
        type=int,
        default=DEFAULT_MIN_TRADES,
        help=f"Minimum resolved trades (default: {DEFAULT_MIN_TRADES})"
    )
    parser.add_argument(
        "--min-win-rate",
        type=float,
        default=DEFAULT_MIN_WIN_RATE,
        help=f"Minimum win rate 0-1 (default: {DEFAULT_MIN_WIN_RATE})"
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=DEFAULT_TOP_N,
        help=f"Fetch top N from leaderboard (default: {DEFAULT_TOP_N})"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Save results to JSON file (e.g. wallets.json)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip activity validation, just show leaderboard results"
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(
        window=args.window,
        min_pnl=args.min_pnl,
        min_trades=args.min_trades,
        min_win_rate=args.min_win_rate,
        top_n=args.top_n,
        output=args.output,
        dry_run=args.dry_run,
    ))
