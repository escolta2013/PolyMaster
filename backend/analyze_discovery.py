import httpx
import json

async def analyze_discovery():
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 500,
        "active": "true",
        "closed": "false",
        "order": "volume",
        "ascending": "false"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            
            total = len(data)
            active_non_closed = 0
            count_01_09 = 0
            skipped_reason = {"closed": 0, "price_extreme": 0, "no_prices": 0}
            
            candidates = []
            
            for m in data:
                if m.get("closed") or m.get("archived") or not m.get("active"):
                    skipped_reason["closed"] += 1
                    continue
                
                active_non_closed += 1
                
                prices_raw = m.get("outcomePrices") or m.get("outcome_prices") or []
                prices = []
                if isinstance(prices_raw, str):
                    try:
                        prices = json.loads(prices_raw)
                    except:
                        pass
                else:
                    prices = prices_raw
                
                if not prices:
                    skipped_reason["no_prices"] += 1
                    continue
                
                try:
                    p = float(prices[0])
                    if 0.10 <= p <= 0.90:
                        count_01_09 += 1
                        candidates.append((m.get("question"), p))
                    else:
                        skipped_reason["price_extreme"] += 1
                except:
                    skipped_reason["no_prices"] += 1
            
            print(f"--- DISCOVERY ANALYSIS ---")
            print(f"Total Markets Fetched: {total}")
            print(f"Active & Non-Closed: {active_non_closed}")
            print(f"Skipped because Price < 0.10 or > 0.90: {skipped_reason['price_extreme']}")
            print(f"Skipped because Closed/Archived: {skipped_reason['closed']}")
            print(f"Skipped because No Prices: {skipped_reason['no_prices']}")
            print(f"MATCH (0.10 <= Price <= 0.90): {count_01_09}")
            print("\nSample candidates (0.10 - 0.90):")
            for q, p in candidates[:15]:
                print(f"- {q[:60]}... (Price: {p})")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(analyze_discovery())
