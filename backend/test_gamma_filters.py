import httpx
import json

async def test_keyset_filters():
    url = "https://gamma-api.polymarket.com/markets/keyset"
    # Testing common filters used in our app
    params = {
        "limit": 5,
        "active": "true",
        "closed": "false"
    }
    print(f"Probando filtros en keyset: {url} con {params}")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            print(f"Status Code: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                markets = data.get("markets", [])
                print(f"✅ Filtros 'active' y 'closed' parecen funcionar.")
                print(f"Recibidos: {len(markets)}")
                if markets:
                    print(f"Ejemplo: {markets[0].get('question')[:50]}")
            else:
                print(f"❌ Error al usar filtros: {resp.status_code}")
                print(f"Tip: Algunos filtros podrían haber cambiado de nombre o no ser compatibles.")
                print(resp.text)
        except Exception as e:
            print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_keyset_filters())
