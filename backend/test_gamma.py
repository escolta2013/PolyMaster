import asyncio
import httpx

async def test_api():
    url = "https://gamma-api.polymarket.com/markets"
    params = {"limit": 100}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        print(f"Total returned: {len(r.json())}")
        
    params = {"limit": 100, "active": "true"}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        print(f"Active returned: {len(r.json())}")

    params = {"limit": 100, "active": "true", "closed": "false"}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        print(f"Active & Not Closed: {len(r.json())}")

if __name__ == "__main__":
    asyncio.run(test_api())
