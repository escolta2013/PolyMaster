
import httpx
import json

def find_ok_market():
    # Fetch top 20 markets
    r = httpx.get('https://gamma-api.polymarket.com/markets?limit=20&order=volume&ascending=false&active=true')
    markets = r.json()
    for m in markets:
        tids_raw = m.get("clobTokenIds") or "[]"
        tids = json.loads(tids_raw) if isinstance(tids_raw, str) else tids_raw
        if not tids: continue
        
        tid = tids[0]
        try:
            resp = httpx.get(f"https://clob.polymarket.com/book?token_id={tid}", timeout=5)
            print(f"Market: {m['question'][:40]}... | Status: {resp.status_code}")
        except Exception as e:
            print(f"Market: {m['question'][:40]}... | Error: {e}")

if __name__ == "__main__":
    find_ok_market()
