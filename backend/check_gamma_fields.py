
import httpx
import json

def check_gamma():
    r = httpx.get('https://gamma-api.polymarket.com/markets?limit=10&order=volume&ascending=false&active=true')
    markets = r.json()
    for m in markets:
        print(f"ID: {m['id']} | Question: {m['question']}")
        print(f"  Volume: {m.get('volume')} | Liquidity: {m.get('liquidity')}")
        print(f"  clobTokenIds: {m.get('clobTokenIds')}")
        print("-" * 20)

if __name__ == "__main__":
    check_gamma()
