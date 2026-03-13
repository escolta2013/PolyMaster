
import httpx
import json

def check_404_gamma():
    r = httpx.get('https://gamma-api.polymarket.com/markets?limit=20&order=volume&ascending=false&active=true')
    markets = r.json()
    for m in markets:
        tids_raw = m.get("clobTokenIds") or "[]"
        tids = json.loads(tids_raw) if isinstance(tids_raw, str) else tids_raw
        if not tids: continue
        
        tid = tids[0]
        resp = httpx.get(f"https://clob.polymarket.com/book?token_id={tid}")
        status = resp.status_code
        
        print(f"Market: {m['question'][:40]}")
        print(f"  CLOB Status: {status}")
        print(f"  Gamma Price: {m.get('lastTradePrice')} | Spread: {m.get('spread')} | Bid: {m.get('bestBid')} | Ask: {m.get('bestAsk')}")
        print("-" * 20)

if __name__ == "__main__":
    check_404_gamma()
