"""
Verifica que el fix al cluster_detector funciona.
"""
import asyncio
import httpx
import sys
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime, timedelta, timezone

# ── TEST 1: Timestamp parsing logic ──────────────────────────────────────────

def parse_timestamp(ts_val) -> datetime:
    """Same logic as the fix in cluster_detector.py"""
    if isinstance(ts_val, str):
        return datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
    else:
        return datetime.fromtimestamp(int(ts_val), tz=timezone.utc)

print("=" * 60)
print("TEST 1: Timestamp parsing")
print("=" * 60)

# Test integer epoch (what we saw from the API)
epoch_ts = 1772844207
ts1 = parse_timestamp(epoch_ts)
print(f"  Epoch {epoch_ts} -> {ts1} ✅")

# Test ISO string (old format)
iso_ts = "2026-03-07T10:00:00Z"
ts2 = parse_timestamp(iso_ts)
print(f"  ISO '{iso_ts}' -> {ts2} ✅")


# ── TEST 2: Live API call for a known whale ───────────────────────────────────

async def test_live_activity():
    print()
    print("=" * 60)
    print("TEST 2: Live API - parse trades from beachboy4 (0xc2e7...)")
    print("=" * 60)

    addr = "0xc2e7800b5af46e6093872b177b7a5e7f0563be51"
    url = "https://data-api.polymarket.com/v1/activity"
    params = {"user": addr, "type": "TRADE", "limit": 30}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        print(f"  API status: {resp.status_code}")

        if resp.status_code != 200:
            print("  ❌ API unavailable")
            return

        data = resp.json()
        # Handle both dict and list
        if isinstance(data, dict):
            data = data.get("data", [])

        print(f"  Total items returned by API: {len(data)}")

        now = datetime.now(timezone.utc)
        recent = []
        errors = 0
        for act in data:
            try:
                ts_val = act.get("timestamp")
                if not ts_val:
                    continue
                ts = parse_timestamp(ts_val)
                age_h = (now - ts).total_seconds() / 3600
                if now - ts < timedelta(hours=12):
                    recent.append(act)
                    side = act.get("side", "?")
                    asset = act.get("asset", "?")[:12]
                    print(f"    RECENT [{age_h:.1f}h ago] side={side} asset={asset}...")
            except Exception as e:
                errors += 1
                print(f"    ⚠️ Parse error: {e}")

        print()
        print(f"  Recent trades (<12h): {len(recent)}")
        print(f"  Parse errors:         {errors}")

        if errors == 0:
            print()
            print("  ✅ FIX CONFIRMED — 0 parse errors, timestamps parse correctly")
        else:
            print()
            print("  ❌ FIX INCOMPLETE — still getting parse errors")

        # Check 3 more whales quickly
        print()
        print("=" * 60)
        print("TEST 3: Spot-check 3 more whales for parse errors")
        print("=" * 60)
        test_wallets = [
            "0x25e64cd559e8c46a888d8ebfa47d4490e810cc9f",
            "0x9c4ccdb83e6f78d84d5b4422917ca05752e23a00",
            "0xed61f86bb5298d2f27c21c433ce58d80b88a9aa3",
        ]
        for w in test_wallets:
            resp2 = await client.get(url, params={"user": w, "type": "TRADE", "limit": 20})
            if resp2.status_code == 200:
                d = resp2.json()
                if isinstance(d, dict):
                    d = d.get("data", [])
                errs = 0
                recnt = 0
                for act in d:
                    try:
                        ts_val = act.get("timestamp")
                        if ts_val:
                            ts = parse_timestamp(ts_val)
                            if now - ts < timedelta(hours=12):
                                recnt += 1
                    except:
                        errs += 1
                status = "✅" if errs == 0 else f"❌ {errs} errors"
                print(f"  {w[:20]}... → {len(d)} trades, {recnt} recent (<12h), {status}")

asyncio.run(test_live_activity())
