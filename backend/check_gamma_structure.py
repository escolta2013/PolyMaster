
import httpx
import json

def check_gamma():
    r = httpx.get('https://gamma-api.polymarket.com/markets?limit=5&order=volume&ascending=false&active=true')
    markets = r.json()
    for m in markets:
        print(f"ID: {m['id']} | Question: {m['question']}")
        print(f"  clobTokenIds: {m.get('clobTokenIds')}")
        print(f"  conditionId: {m.get('conditionId')}")
        print("-" * 20)

if __name__ == "__main__":
    check_gamma()
