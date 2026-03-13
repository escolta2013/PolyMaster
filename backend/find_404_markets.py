
import httpx
import json

def find_404_market():
    # Fetch top 100 markets
    r = httpx.get('https://gamma-api.polymarket.com/markets?limit=100&order=volume&ascending=false&active=true')
    markets = r.json()
    for m in markets:
        tids_raw = m.get("clobTokenIds") or "[]"
        tids = json.loads(tids_raw) if isinstance(tids_raw, str) else tids_raw
        if not tids: continue
        
        tid = tids[0]
        resp = httpx.get(f"https://clob.polymarket.com/book?token_id={tid}")
        if resp.status_code == 404:
            print(f"404 Market: {m['question']}")
            print(f"  TID: {tid}")
        else:
            print(f"OK Market: {m['question']} (Status: {resp.status_code})")

if __name__ == "__main__":
    find_404_market()
