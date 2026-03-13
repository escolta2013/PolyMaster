"""Quick debug: what does the Gamma API actually return for a resolved market?"""
import asyncio
import httpx

GAMMA_API = "https://gamma-api.polymarket.com"

# Market IDs from the bot's WOULD_EXECUTE log
# Thunder vs Raptors (should be resolved by now)
# Spread: Mavericks (-1.5) (should be resolved - same-day sports)
TEST_IDS = [
    "1392394",   # Thunder vs. Raptors
    "1421515",   # Spread: Mavericks (-1.5)
    "629338",    # Will the Republicans win the Georgia governor race (long-term)
    "540819",    # Will Jesus Christ return before GTA VI (long-term)
]

async def main():
    async with httpx.AsyncClient() as client:
        for mid in TEST_IDS:
            print(f"\n{'='*60}")
            print(f"Market ID: {mid}")
            try:
                resp = await client.get(f"{GAMMA_API}/markets/{mid}", timeout=10)
                data = resp.json()
                
                # Print all resolution-relevant fields
                keys_of_interest = [
                    "question", "closed", "resolved", "outcome",
                    "outcomePrices", "acceptingOrders", "active",
                    "enableOrderBook", "endDate", "endDateIso",
                    "resolutionSource", "conditionId", "questionID",
                    "winner", "marketMakerAddress", "volume",
                ]
                for k in keys_of_interest:
                    if k in data:
                        v = data[k]
                        if isinstance(v, str) and len(v) > 80:
                            v = v[:80] + "..."
                        print(f"  {k}: {v}")
                
                # Also check for any field containing 'resol' or 'close' or 'outcome'
                for k, v in data.items():
                    if any(word in k.lower() for word in ['resol', 'close', 'outcome', 'winner', 'settled']):
                        if k not in keys_of_interest:
                            print(f"  [EXTRA] {k}: {v}")
                            
            except Exception as e:
                print(f"  ERROR: {e}")

asyncio.run(main())
