import httpx
import asyncio

async def test_api():
    async with httpx.AsyncClient() as client:
        addr = "0xc2e7800b5af46e6093872b177b7a5e7f0563be51"  # beachboy4
        url = "https://data-api.polymarket.com/v1/activity"
        params = {"user": addr, "limit": 10}
        resp = await client.get(url, params=params)
        print("Status:", resp.status_code)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                print("Keys:", data.keys())
                data = data.get("data", [])
            print("Items count:", len(data))
            if data:
                print("First item:", data[0])

if __name__ == "__main__":
    asyncio.run(test_api())
