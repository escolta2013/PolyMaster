
import httpx
import json

def find_ok_market():
    # Fetch top 200 markets
    r = httpx.get('https://gamma-api.polymarket.com/markets?limit=200&order=volume&ascending=false&active=true')
    markets = r.json()
    ok_count = 0
    fail_count = 0
    for m in markets:
        tids_raw = m.get("clobTokenIds") or "[]"
        tids = json.loads(tids_raw) if isinstance(tids_raw, str) else tids_raw
        if not tids: continue
        
        tid = tids[0]
        resp = httpx.get(f"https://clob.polymarket.com/book?token_id={tid}")
        if resp.status_code == 200:
            print(f"OK Market: {m['question']}")
            print(f"  TID: {tid}")
            ok_count += 1
            if ok_count >= 5: break
        else:
            fail_count += 1
            
    print(f"\nSummary: {ok_count} OK, {fail_count} Fails (404)")

if __name__ == "__main__":
    find_ok_market()
