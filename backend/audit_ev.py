"""
Audit EV: Calculates real Expected Value and ROI based on actual entry prices.
Also simulates production filter survival.
"""
import asyncio
import re
import json
import httpx
from pathlib import Path
from typing import Optional, List, Tuple, Dict

LOG_PATH = Path(__file__).parent / "logs" / "autonomous.log"
GAMMA_API = "https://gamma-api.polymarket.com"

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
    r"\[PAPER\] Logged (?P<decision>WOULD_EXECUTE|PAPER_REJECTED) for (?P<mid>\d+)"
)

def safe_parse_outcome_prices(raw) -> Tuple[Optional[float], Optional[float]]:
    if raw is None: return None, None
    if isinstance(raw, str):
        try: raw = json.loads(raw)
        except: return None, None
    if isinstance(raw, list) and len(raw) >= 2:
        try: return float(raw[0]), float(raw[1])
        except: return None, None
    return None, None

async def main():
    print("Reading logs for EV Analysis...")
    content = ""
    for p in sorted(Path("logs").glob("autonomous*.log"), reverse=True):
        content += p.read_text(encoding="utf-8", errors="replace")
    
    lines = content.splitlines()
    records = {}
    
    for i, line in enumerate(lines):
        m = DECISION_PATTERN.search(line)
        if m:
            for j in range(i+1, min(i+10, len(lines))):
                lm = LOGGED_PATTERN.search(lines[j])
                if lm:
                    mid = lm.group("mid")
                    if mid not in records:
                        records[mid] = {
                            "mid": mid,
                            "name": m.group("market"),
                            "ask": float(m.group("ask")),
                            "spread": float(m.group("spread")),
                            "edge_net": float(m.group("edge_net")),
                            "decision": m.group("decision")
                        }
                    break

    print(f"Analyzing {len(records)} unique markets...")
    
    wins, losses, total = 0, 0, 0
    total_roi = 0.0
    survivors = 0
    
    # We want accuracy only for WOULD_EXECUTE that resolved
    # And we want potential win ROI for ALL WOULD_EXECUTE
    all_we_potential_roi = []

    async with httpx.AsyncClient() as client:
        for mid, rec in records.items():
            try:
                # Stats for ALL unique markets
                is_we = (rec["decision"] == "WOULD_EXECUTE")
                if is_we:
                    all_we_potential_roi.append( (1.0 / rec["ask"]) - 1.0 )

                # Production Filter Check
                if rec["spread"] <= 0.15 and rec.get("edge_net", 0) >= 0.05:
                    survivors += 1

                # Resolution
                resp = await client.get(f"{GAMMA_API}/markets/{mid}", timeout=10)
                data = resp.json()
                p1, _ = safe_parse_outcome_prices(data.get("outcomePrices"))
                closed = data.get("closed", False)
                
                won_yes = None
                if closed and data.get("outcome") is not None:
                    o = str(data.get("outcome")).strip().upper()
                    if o in ("YES", "1", "TRUE"): won_yes = True
                    else: won_yes = False
                elif p1 is not None:
                    if p1 >= 0.95: won_yes = True
                    elif p1 <= 0.05: won_yes = False

                if won_yes is not None and is_we:
                    total += 1
                    if won_yes:
                        roi = (1.0 / rec["ask"]) - 1.0
                        wins += 1
                        total_roi += roi
                    else:
                        roi = -1.0
                        losses += 1
                        total_roi += roi
                    
                    if any(kw in rec["name"] for kw in ["Counter-Strike", "Atalanta", "Real Sociedad"]):
                        status = "WIN" if won_yes else "LOSS"
                        print(f"!!! TARGET: {rec['name'][:40]} | Result: {status} | Ask: {rec['ask']} | ROI: {roi:+.2%}")

            except Exception as e:
                continue

    print(f"\n{'='*60}")
    print(f"--- REAL ROI & EV AUDIT ---")
    print(f"{'='*60}")
    print(f"Total WOULD_EXECUTE Resolved: {total}")
    print(f"Accuracy: {wins/total*100:.1f}% ({wins}/{total})")
    
    if total > 0:
        avg_roi_real = total_roi / total
        print(f"Average Actual ROI (across these {total} trades): {avg_roi_real:+.2%}")
        
        avg_win_potential = sum(all_we_potential_roi)/len(all_we_potential_roi) if all_we_potential_roi else 0
        acc_rate = wins / total
        ev = (acc_rate * avg_win_potential) - ((1 - acc_rate) * 1.0)
        
        print(f"Average Possible Gain (1/Ask - 1): {avg_win_potential:+.2%}")
        print(f"Average Possible Loss: -100.00%")
        print(f"Calculated EV: {ev:+.4f}")
        
    print(f"\n--- PRODUCTION FILTER SIMULATION ---")
    print(f"Markets analyzed: {len(records)}")
    print(f"Survivors (Spread <= 0.15 & Edge Net >= 0.05): {survivors}")
    print(f"Survival Rate: {survivors/len(records)*100:.1f}%")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())
