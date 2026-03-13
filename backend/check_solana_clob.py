
import httpx
import json

def check_solana():
    # Search for Solana markets
    r = httpx.get('https://gamma-api.polymarket.com/markets?limit=5&active=true&closed=false&q=Solana')
    markets = r.json()
    for m in markets:
        print(f"ID: {m['id']} | Question: {m['question']}")
        tids_raw = m.get("clobTokenIds") or "[]"
        tids = json.loads(tids_raw) if isinstance(tids_raw, str) else tids_raw
        print(f"  TIDs: {tids}")
        
        # Try fetching orderbook for each TID
        for tid in tids:
            resp = httpx.get(f"https://clob.polymarket.com/book?token_id={tid}")
            print(f"    TID {tid}: {resp.status_code}")
        print("-" * 20)

if __name__ == "__main__":
    check_solana()
