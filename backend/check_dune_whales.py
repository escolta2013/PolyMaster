import httpx
import asyncio

WALLETS = [
    "0x1abe1368601330a310162064e04d3c2628cb6497",
    "0x8f42ae0a01c0383c7ca8bd060b86a645ee74b88f",
    "0xbc43a2f0deb85ba4ad316300762972089c911540",
    "0xae7c98235d5dc797edfa3d3af2e0334238a4487e",
    "0xbb015bb4009b6a48bfb9363d9c9b1d54e9ab02e5",
    "0x99dd407b80e45874638d783f54b0d8c097544303",
    "0x1057e7d3ddafc60a4aeb10a2bc5b543792449ea5",
    "0xe1194d05876b71b05572c1b59bd49a157f21e30f",
    "0xc0292a841a0c9a7320aa39075cffcf1b8f64f705",
    "0xf1f02c72c0b8f6a70773b61d4ff16bccc14178cd",
    "0x57dedd62596dd4f85c7ebe5317e07d22795ecd90",
    "0xe617861a96631d7cefdb1ad43e95c33b5946f251",
    "0xbce2ae81dded77a0fdf69c4ea2b4869d6b5d0ab4",
    "0x50dea44f96beebc78725542bb3afd1ad1998c9b7",
    "0xde7be6d489bce070a959e0cb813128ae659b5f4b",
    "0xaac2469db4c243a2931acc252967b171bd97e8ce",
    "0xc311bbe0d55797afa70c9329e15157640a6e44fc",
    "0xc3e45193d37ec34b82129adfc46abff7bb415bf6",
    "0xf60ec79ce74057d448754b9f51195d13b085936d",
    "0x7e6fda10646a4343358c84004859adfea1c0c022",
    "0x2a6685afdc97f988d5c715c34a0fa42e9bc6629e",
    "0x986b121c40e715167dde178b8520bf132a57bdc6",
    "0xdfafd14f51d8f163a2df19144275233dc598aeb4",
    "0xe385cc339e6dd3abca1fcdf84055f9afd9c0dd7f",
    "0x9910712aacd5a9fe057e12b1d10a789b939f5058",
    "0xb111b717ca0b17d997cf3cd796798e82a7b4ba0c",
    "0x9ec7da81a2da3d47a47dd281b1ecf2cf2b3a35c0",
    "0xaa9ae1ef7719af8694d6811817c6d0c22aa43b3e",
    "0xcd95ebd0d0d099fa442b9730991f2b8be5d28c17",
]

# remove duplicates
WALLETS = list(set(WALLETS))

async def check_wallets():
    async with httpx.AsyncClient() as client:
        for wallet in WALLETS:
            url = "https://data-api.polymarket.com/v1/activity"
            params = {"user": wallet, "limit": 50}
            print(f"\\n--- Checking {wallet} ---")
            
            try:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    trades = data if isinstance(data, list) else data.get("data", [])
                    
                    if not trades:
                        print("No recent trades.")
                        continue
                        
                    prices = []
                    for t in trades:
                        if t.get("price"):
                            try:
                                prices.append(float(t["price"]))
                            except:
                                pass
                                
                    if prices:
                        avg_price = sum(prices) / len(prices)
                        print(f"Average entry price (last {len(prices)} trades): {avg_price:.3f}")
                        
                        # Check if penny picking
                        penny_trades = sum(1 for p in prices if p >= 0.90 or p <= 0.10)
                        print(f"Trades > 0.90 or < 0.10: {penny_trades}/{len(prices)} ({penny_trades/len(prices):.1%})")
                        
                        if penny_trades / len(prices) > 0.8:
                            print("⚠️ LIKELY PENNY PICKER")
                        else:
                            print("✅ GOOD TRADER PROFILE")
                    else:
                        print("No price data in recent activity.")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_wallets())
