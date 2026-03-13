
import httpx
import asyncio
import json

async def inspect_wallet(address: str, name: str):
    url = "https://data-api.polymarket.com/v1/activity"
    params = {
        "user": address,
        "limit": 20,
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    
    print(f"\n--- Inspecting {name} ({address}) ---")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                print(f"Error {resp.status_code}: {resp.text}")
                return
                
            data = resp.json()
            # Handle list or dict wrapped list
            if isinstance(data, dict):
                trades = data.get("data", [])
            else:
                trades = data

            if trades:
                print("\n--- RAW DATA SAMPLE (Trade 1) ---")
                print(json.dumps(trades[0], indent=2))

            for i, t in enumerate(trades):
                # Data API activity usually includes price, side, and outcome
                price = t.get("price")
                side = t.get("side") # Buy/Sell
                q = t.get("question") or t.get("market", "Unknown")
                pnl = t.get("pnl")
                
                print(f"{i+1}. Q: {str(q)[:60]}...")
                print(f"   Price: {price} | PnL: {pnl}")
        except Exception as e:
            print(f"Inspection failed: {e}")

if __name__ == "__main__":
    # Inspecting joosangyoo
    asyncio.run(inspect_wallet("0x07b8e44b90cc3e91b8d5fe60ea810d2534638e25", "joosangyoo"))
