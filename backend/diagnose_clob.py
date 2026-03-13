
import httpx
import json

def diagnose():
    # 1. Fetch the Solana market specifically
    r = httpx.get('https://gamma-api.polymarket.com/markets?q=Solana&active=true')
    markets = r.json()
    if markets:
        m = markets[0]
        print(f"Market: {m['question']}")
        tids = m.get('clobTokenIds', [])
        if isinstance(tids, str): tids = json.loads(tids)
        print(f"TIDs from Gamma: {tids}")
        
        for tid in tids:
            # Try official CLOB API
            url = f"https://clob.polymarket.com/book?token_id={tid}"
            resp = httpx.get(url)
            print(f"  TID {tid} -> {resp.status_code}")
            if resp.status_code == 200:
                print(f"    Book: {resp.json().get('bids', [])[:1]}...")

    # 2. Fetch the Counter-Strike market that failed
    r = httpx.get('https://gamma-api.polymarket.com/markets?q=Acend&active=true')
    markets = r.json()
    if markets:
        m = markets[0]
        print(f"\nMarket: {m['question']}")
        tids = m.get('clobTokenIds', [])
        if isinstance(tids, str): tids = json.loads(tids)
        print(f"TIDs from Gamma: {tids}")
        
        for tid in tids:
            url = f"https://clob.polymarket.com/book?token_id={tid}"
            resp = httpx.get(url)
            print(f"  TID {tid} -> {resp.status_code}")

if __name__ == "__main__":
    diagnose()
