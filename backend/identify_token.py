import httpx
import asyncio

async def identify_token(token_id: str):
    url = f"https://clob.polymarket.com/markets/{token_id}"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url)
            print(f"CLOB Status: {r.status_code}")
            if r.status_code == 200:
                print("CLOB Data:", r.json())
            else:
                print(f"CLOB Error: {r.text}")
        except Exception as e:
            print(f"CLOB Exception: {e}")

    # Also try Gamma
    url = f"https://gamma-api.polymarket.com/markets"
    # Gamma doesn't have a direct token_id lookup by path, need to search
    params = {"clobTokenId": token_id}
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, params={"clobTokenIds": f"[\"{token_id}\"]"})
            print(f"Gamma Status: {r.status_code}")
            if r.status_code == 200:
                print("Gamma Data:", r.json())
        except Exception as e:
            print(f"Gamma Exception: {e}")

if __name__ == "__main__":
    tid = "56038619117216105571869034381769885866198115858034311111792518496797122345928"
    asyncio.run(identify_token(tid))
