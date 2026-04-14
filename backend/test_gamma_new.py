import httpx
import json

async def test_new_api():
    url = "https://gamma-api.polymarket.com/markets/keyset"
    params = {"limit": 5}
    print(f"Probando nuevo endpoint: {url}")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            print(f"Status Code: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                markets = data.get("markets", [])
                next_cursor = data.get("next_cursor")
                print(f"✅ ¡La API nueva ya está ACTIVA!")
                print(f"Mercados recibidos: {len(markets)}")
                print(f"Next Cursor: {next_cursor}")
            else:
                print(f"❌ La API respondió con error: {resp.status_code}")
                print(resp.text)
        except Exception as e:
            print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_new_api())
