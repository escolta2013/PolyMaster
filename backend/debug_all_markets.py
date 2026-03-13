"""Debug: Check outcomePrices for ALL 31 unique WOULD_EXECUTE markets."""
import asyncio
import re
import json
import httpx
from pathlib import Path

LOG_PATH = Path(__file__).parent / "logs" / "autonomous.log"
GAMMA_API = "https://gamma-api.polymarket.com"

EXEC_PATTERN = re.compile(
    r"\[PAPER\] WOULD_EXECUTE \| "
    r"Market: (?P<market>.+?) \| "
    r"Council: (?P<council>[\d.]+) \| "
    r"Ask: (?P<ask>[\d.]+)"
)
LOGGED_PATTERN = re.compile(
    r"\[PAPER\] Logged WOULD_EXECUTE for (?P<market_id>\d+)"
)

def parse_unique_markets():
    lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    exec_entries = []
    for i, line in enumerate(lines):
        m = EXEC_PATTERN.search(line)
        if m:
            exec_entries.append({"line_idx": i, "market": m.group("market"), "ask": m.group("ask")})
    
    trades = []
    seen = set()
    for entry in exec_entries:
        start = entry["line_idx"] + 1
        end = min(start + 5, len(lines))
        for j in range(start, end):
            lm = LOGGED_PATTERN.search(lines[j])
            if lm:
                mid = lm.group("market_id")
                if mid not in seen:
                    seen.add(mid)
                    trades.append({"market_id": mid, "market_name": entry["market"], "ask": entry["ask"]})
                break
    return trades

def safe_parse_outcome_prices(raw):
    """Parse outcomePrices which can be a string, list, or None."""
    if raw is None:
        return None, None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except:
            return None, None
    if isinstance(raw, list) and len(raw) >= 2:
        try:
            return float(raw[0]), float(raw[1])
        except:
            return None, None
    return None, None

async def main():
    trades = parse_unique_markets()
    print(f"Found {len(trades)} unique WOULD_EXECUTE markets\n")
    
    wins = 0
    losses = 0
    open_count = 0
    
    async with httpx.AsyncClient() as client:
        for t in trades:
            try:
                resp = await client.get(f"{GAMMA_API}/markets/{t['market_id']}", timeout=10)
                data = resp.json()
                
                p1, p2 = safe_parse_outcome_prices(data.get("outcomePrices"))
                outcomes = data.get("outcomes", [])
                closed = data.get("closed", "?")
                uma = data.get("umaResolutionStatus", "none")
                end = data.get("endDate", "?")
                
                # Status determination
                if p1 is not None:
                    if p1 >= 0.95:
                        status = " WIN"
                        wins += 1
                    elif p1 <= 0.05:
                        status = "LOSS"
                        losses += 1
                    else:
                        status = "OPEN"
                        open_count += 1
                else:
                    status = "  ? "
                
                p1_str = f"{p1:.4f}" if p1 is not None else "?"
                print(f"[{status}] {t['market_id']:>10} | P1={p1_str:>7} | Close={str(closed):>5} | UMA={str(uma):>8} | End={str(end)[:20]:>20} | {t['market_name'][:55]}")
            except Exception as e:
                print(f"[ERR ] {t['market_id']:>10} | {e} | {t['market_name'][:55]}")

    print(f"\n{'='*60}")
    print(f"SUMMARY: {wins} WINS | {losses} LOSSES | {open_count} OPEN")
    if wins + losses > 0:
        print(f"ACCURACY: {wins/(wins+losses)*100:.1f}% ({wins}/{wins+losses})")
    print(f"{'='*60}")

asyncio.run(main())
