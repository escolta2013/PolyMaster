
import httpx
import asyncio
import json

LEADERBOARD_URL = "https://data-api.polymarket.com/v1/leaderboard"
USERNAMES = ["domahhh", "ImJustKen", "aenews", "aenews2", "gopfan2", "HolyMoses", "HolyMoses7", "Frosenn"]

async def find_users():
    found = []
    async with httpx.AsyncClient() as client:
        # Try different windows just in case
        for window in ["all", "30d", "7d"]:
            print(f"Searching window: {window}...")
            params = {
                "window": window,
                "limit": 1000, # Large limit to find these specific ones
                "sortBy": "pnl"
            }
            try:
                resp = await client.get(LEADERBOARD_URL, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    # It's usually a list
                    traders = data if isinstance(data, list) else data.get("data", [])
                    
                    for t in traders:
                        uname = t.get("userName") or ""
                        if any(u.lower() == uname.lower() for u in USERNAMES):
                            if t not in found:
                                found.append(t)
                                print(f"Found: {uname} -> {t.get('proxyWallet')}")
            except Exception as e:
                print(f"Error: {e}")
                
    print("\n--- Summary ---")
    for f in found:
        print(f"Username: {f.get('userName')} | Wallet: {f.get('proxyWallet')}")
    return found

if __name__ == "__main__":
    asyncio.run(find_users())
