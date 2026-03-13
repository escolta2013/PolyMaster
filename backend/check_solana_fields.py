
import httpx
import json

def check_solana_fields():
    r = httpx.get('https://gamma-api.polymarket.com/markets?q=Solana&active=true&closed=false')
    markets = r.json()
    if markets:
        m = markets[0]
        # Only print keys that look like volume or price
        print(f"Question: {m['question']}")
        for k, v in m.items():
            if 'volume' in k.lower() or 'price' in k.lower() or 'bid' in k.lower() or 'ask' in k.lower() or 'spread' in k.lower():
                print(f"  {k}: {v}")

if __name__ == "__main__":
    check_solana_fields()
