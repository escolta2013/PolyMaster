"""
Extended Audit: Covers ALL bot decisions (WOULD_EXECUTE + PAPER_REJECTED)
and checks which ones resolved today.

For WOULD_EXECUTE (bot bought YES):
  - Resolved YES → WIN (correct buy)
  - Resolved NO  → LOSS (wrong buy)

For PAPER_REJECTED (bot refused to buy YES):
  - Resolved NO  → CORRECT REJECTION (would have lost)
  - Resolved YES → MISSED OPPORTUNITY (would have won)

This gives us the full picture of Council accuracy.
"""
import asyncio
import re
import json
import httpx
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple

LOG_PATH = Path(__file__).parent / "logs" / "autonomous.log"
GAMMA_API = "https://gamma-api.polymarket.com"

# ── Patterns ──
DECISION_PATTERN = re.compile(
    r"\[PAPER\] (?P<decision>WOULD_EXECUTE|PAPER_REJECTED) \| "
    r"Market: (?P<market>.+?) \| "
    r"Council: (?P<council>[\d.]+) \| "
    r"Ask: (?P<ask>[\d.]+) \| "
    r"Spread: (?P<spread>[\d.]+) \| "
    r"Edge Brute: (?P<edge_brute>[+\-][\d.]+) \| "
    r"Edge Net: (?P<edge_net>[+\-][\d.]+)"
)
LOGGED_PATTERN = re.compile(
    r"(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+).*"
    r"\[PAPER\] Logged (?P<decision>WOULD_EXECUTE|PAPER_REJECTED) for (?P<mid>\d+)"
)

SPORTS_KW = [
    "vs.", "o/u", "spread:", "nba", "nfl", "mlb", "nhl", "ufc",
    "win on 2026", "mavericks", "thunder", "lakers", "celtics",
    "bucks", "raptors", "warriors", "cavaliers", "hawks", "bulls",
    "heat", "nets", "pacers", "hornets", "magic", "suns", "pelicans",
    "real sociedad", "galatasaray", "crvena zvezda",
    "fk ", "psg", "liga", "ligue", "serie a",
    "rebounds", "assists", "points", "handicap",
    "predators", "blackhawks", "mountaineers", "cowboys", "cyclones",
    "chanticleers", "panthers", "wolfpack", "cavaliers", "horned frogs",
    "wolf pack", "76ers", "dota 2", "counter-strike",
    "open:", "akron:", "game 1", "game 2",
]


def classify(name):
    low = name.lower()
    if any(kw in low for kw in SPORTS_KW):
        return "Sports"
    if any(kw in low for kw in ["bitcoin", "ethereum", "solana", "xrp", "bnb", "token", "fdv", "dip to", "reach $"]):
        return "Crypto"
    if any(kw in low for kw in ["trump", "republican", "democrat", "governor", "senate", "russia", "israel", "election"]):
        return "Politics"
    return "Other"


def safe_parse_outcome_prices(raw) -> Tuple[Optional[float], Optional[float]]:
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


def parse_all_decisions():
    """Parse ALL decisions (WOULD_EXECUTE + PAPER_REJECTED)."""
    print(f"Reading log...")
    lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"  Total lines: {len(lines):,}")
    
    # Find all decision lines
    decision_entries = []
    for i, line in enumerate(lines):
        m = DECISION_PATTERN.search(line)
        if m:
            decision_entries.append({
                "line_idx": i,
                "decision": m.group("decision"),
                "market": m.group("market"),
                "council": float(m.group("council")),
                "ask": float(m.group("ask")),
                "spread": float(m.group("spread")),
                "edge_brute": float(m.group("edge_brute")),
                "edge_net": float(m.group("edge_net")),
            })
    
    print(f"  Total decision lines: {len(decision_entries)}")
    
    # Match to market_ids (deduped - keep first occurrence)
    records = {}
    for entry in decision_entries:
        start = entry["line_idx"] + 1
        end = min(start + 5, len(lines))
        for j in range(start, end):
            lm = LOGGED_PATTERN.search(lines[j])
            if lm:
                mid = lm.group("mid")
                if mid not in records:
                    records[mid] = {
                        "market_id": mid,
                        "decision": entry["decision"],
                        "market_name": entry["market"],
                        "council": entry["council"],
                        "ask": entry["ask"],
                        "spread": entry["spread"],
                        "edge_net": entry["edge_net"],
                        "category": classify(entry["market"]),
                        "timestamp": lm.group("ts"),
                    }
                break
    
    by_type = defaultdict(int)
    by_cat = defaultdict(int)
    for r in records.values():
        by_type[r["decision"]] += 1
        by_cat[r["category"]] += 1
    
    print(f"  Unique markets: {len(records)}")
    print(f"  By decision: {dict(by_type)}")
    print(f"  By category: {dict(by_cat)}")
    
    return list(records.values())


async def check_all(records):
    """Check resolution for all records."""
    sem = asyncio.Semaphore(15)
    
    async def check_one(client, rec):
        async with sem:
            try:
                resp = await client.get(f"{GAMMA_API}/markets/{rec['market_id']}", timeout=10)
                data = resp.json()
                
                p1, p2 = safe_parse_outcome_prices(data.get("outcomePrices"))
                rec["p1"] = p1
                rec["closed"] = data.get("closed", False)
                rec["uma"] = data.get("umaResolutionStatus", "")
                rec["end_date"] = data.get("endDate", "")
                rec["outcomes"] = data.get("outcomes", [])
                rec["outcome_field"] = data.get("outcome")
                
                # Determine resolution
                if rec["closed"] and rec["outcome_field"] is not None:
                    rec["status"] = "RESOLVED"
                    # Check if first outcome won
                    o = str(rec["outcome_field"]).strip().upper()
                    outcomes_list = rec["outcomes"]
                    if isinstance(outcomes_list, str):
                        try:
                            outcomes_list = json.loads(outcomes_list)
                        except:
                            outcomes_list = []
                    if o in ("YES", "1", "TRUE") or (outcomes_list and o == str(outcomes_list[0]).strip().upper()):
                        rec["won_yes"] = True
                    else:
                        rec["won_yes"] = False
                elif p1 is not None and p1 >= 0.95:
                    rec["status"] = "RESOLVED"
                    rec["won_yes"] = True
                elif p1 is not None and p1 <= 0.05:
                    rec["status"] = "RESOLVED"
                    rec["won_yes"] = False
                elif rec["uma"] == "proposed" and p1 is not None and p1 >= 0.90:
                    rec["status"] = "RESOLVED"
                    rec["won_yes"] = True
                elif rec["uma"] == "proposed" and p1 is not None and p1 <= 0.10:
                    rec["status"] = "RESOLVED"
                    rec["won_yes"] = False
                else:
                    rec["status"] = "OPEN"
                    rec["won_yes"] = None
            except Exception as e:
                rec["status"] = "ERROR"
                rec["won_yes"] = None
    
    async with httpx.AsyncClient() as client:
        tasks = [check_one(client, r) for r in records]
        await asyncio.gather(*tasks)
    
    return records


def report(records):
    resolved = [r for r in records if r.get("status") == "RESOLVED"]
    open_recs = [r for r in records if r.get("status") == "OPEN"]
    
    print(f"\n{'='*80}")
    print(f"  FULL COUNCIL AUDIT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*80}")
    
    print(f"\n  Total unique markets analyzed: {len(records)}")
    print(f"  Resolved: {len(resolved)}  |  Open: {len(open_recs)}")
    
    # ── Split resolved by decision type ──
    we_resolved = [r for r in resolved if r["decision"] == "WOULD_EXECUTE"]
    pr_resolved = [r for r in resolved if r["decision"] == "PAPER_REJECTED"]
    
    # WOULD_EXECUTE accuracy: win if market resolved YES
    we_wins = sum(1 for r in we_resolved if r["won_yes"])
    we_losses = sum(1 for r in we_resolved if not r["won_yes"])
    
    # PAPER_REJECTED accuracy: correct if market resolved NO (we were right to skip)
    # or if edge_net was actually negative and it resolved YES (we correctly identified no edge)
    pr_correct_skip = sum(1 for r in pr_resolved if not r["won_yes"])  # NO won = right to not buy YES
    pr_missed = sum(1 for r in pr_resolved if r["won_yes"])  # YES won = we missed it
    
    print(f"\n  ── WOULD_EXECUTE (Bot bought YES) ──")
    if we_resolved:
        we_acc = we_wins / len(we_resolved) * 100
        print(f"  Wins: {we_wins}  |  Losses: {we_losses}  |  Total: {len(we_resolved)}")
        print(f"  ACCURACY: {we_acc:.1f}%")
        
        # P&L
        pnl = sum(
            10 * (1.0 / r["ask"]) - 10 if r["won_yes"] else -10
            for r in we_resolved
        )
        print(f"  P&L ($10/trade): ${pnl:+.2f}")
    else:
        print(f"  No resolved WOULD_EXECUTE markets yet.")
    
    print(f"\n  ── PAPER_REJECTED (Bot skipped YES) ──")
    if pr_resolved:
        pr_acc = pr_correct_skip / len(pr_resolved) * 100
        print(f"  Correct Rejections: {pr_correct_skip}  |  Missed Opportunities: {pr_missed}  |  Total: {len(pr_resolved)}")
        print(f"  REJECTION ACCURACY: {pr_acc:.1f}%")
        
        # Simulated loss avoided
        avoided = sum(10 for r in pr_resolved if not r["won_yes"])
        print(f"  Losses Avoided: ${avoided:.2f}")
    else:
        print(f"  No resolved PAPER_REJECTED markets yet.")
    
    # ── Combined accuracy ──
    if resolved:
        # Overall: did the Council make the right call?
        # WOULD_EXECUTE + YES won = correct
        # PAPER_REJECTED + NO won = correct
        total_correct = we_wins + pr_correct_skip
        total_acc = total_correct / len(resolved) * 100
        print(f"\n  ── COMBINED COUNCIL ACCURACY ──")
        print(f"  Correct Decisions: {total_correct}/{len(resolved)} = {total_acc:.1f}%")
    
    # ── Segmented by Edge bucket (WOULD_EXECUTE only) ──
    if we_resolved:
        print(f"\n  ── WOULD_EXECUTE BY EDGE NET ──")
        print(f"  {'Bucket':<12} {'W':>3} {'L':>3} {'Tot':>4} {'Acc':>7} {'P&L':>9}")
        
        buckets = defaultdict(list)
        for r in we_resolved:
            en = abs(r["edge_net"])
            if en < 0.07:
                buckets["0.03-0.07"].append(r)
            elif en < 0.12:
                buckets["0.07-0.12"].append(r)
            else:
                buckets[">0.12"].append(r)
        
        for bk in ["0.03-0.07", "0.07-0.12", ">0.12"]:
            g = buckets.get(bk, [])
            if not g:
                print(f"  {bk:<12} {'—':>3} {'—':>3} {0:>4} {'N/A':>7} {'N/A':>9}")
                continue
            w = sum(1 for r in g if r["won_yes"])
            l = len(g) - w
            acc = w / len(g) * 100
            p = sum(10*(1.0/r["ask"])-10 if r["won_yes"] else -10 for r in g)
            print(f"  {bk:<12} {w:>3} {l:>3} {len(g):>4} {acc:>6.1f}% ${p:>+8.2f}")
    
    # ── By Category (WOULD_EXECUTE only) ──
    if we_resolved:
        print(f"\n  ── WOULD_EXECUTE BY CATEGORY ──")
        print(f"  {'Category':<12} {'W':>3} {'L':>3} {'Tot':>4} {'Acc':>7}")
        cats = defaultdict(list)
        for r in we_resolved:
            cats[r["category"]].append(r)
        for c in sorted(cats.keys()):
            g = cats[c]
            w = sum(1 for r in g if r["won_yes"])
            print(f"  {c:<12} {w:>3} {len(g)-w:>3} {len(g):>4} {w/len(g)*100:>6.1f}%")
    
    # ── Sports markets still OPEN (potential resolutions today) ──
    open_sports = [r for r in open_recs if r.get("category") == "Sports"]
    if open_sports:
        print(f"\n  ── SPORTS MARKETS STILL OPEN ({len(open_sports)}) ──")
        print(f"  These will resolve soon and expand the sample:")
        for r in sorted(open_sports, key=lambda x: x.get("end_date", "9999")):
            end = r.get("end_date", "?")[:16]
            p1 = r.get("p1")
            p1s = f"{p1:.3f}" if p1 else "?"
            dec = "BUY" if r["decision"] == "WOULD_EXECUTE" else "SKIP"
            print(f"  [{dec:>4}] P1={p1s:>6} | Ends={end} | Edge={r['edge_net']:+.3f} | {r['market_name'][:50]}")
    
    # ── Full sample summary ──
    # How many sports resolved TODAY (end_date is Feb 24/25)
    today_sports = [r for r in resolved if r.get("category") == "Sports" 
                    and "2026-02-2" in r.get("end_date", "")]
    print(f"\n  ── SPORTS RESOLVED TODAY: {len(today_sports)} ──")
    
    # Total verifiable pool
    all_sports = [r for r in records if r.get("category") == "Sports"]
    all_sports_end_today = [r for r in all_sports if "2026-02-25" in r.get("end_date", "")]
    print(f"  Total sports markets with endDate Feb 25: {len(all_sports_end_today)}")
    print(f"  Already resolved: {sum(1 for r in all_sports_end_today if r.get('status')=='RESOLVED')}")
    print(f"  Still open (will resolve soon): {sum(1 for r in all_sports_end_today if r.get('status')=='OPEN')}")
    
    print(f"\n{'='*80}")


async def main():
    records = parse_all_decisions()
    records = await check_all(records)
    report(records)


if __name__ == "__main__":
    asyncio.run(main())
