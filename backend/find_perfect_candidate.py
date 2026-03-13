
import httpx
import json

def find_perfect_candidate():
    r = httpx.get('https://gamma-api.polymarket.com/markets?limit=100&order=volume&ascending=false&active=true&closed=false')
    markets = r.json()
    
    print("Checking for markets that SHOULD pass but might be failing depth/clob...")
    for m in markets:
        bid = m.get('bestBid')
        ask = m.get('bestAsk')
        if bid and ask:
            b, a = float(bid), float(ask)
            mid = (a + b) / 2
            s = float(m.get('spread') or (a - b))
            if 0.1 <= mid <= 0.9 and s <= 0.25:
                # This is a candidate Gamma says is good.
                # Now check CLOB
                tids_raw = m.get("clobTokenIds", "[]")
                tids = json.loads(tids_raw) if isinstance(tids_raw, str) else tids_raw
                if tids:
                    tid = tids[0]
                    resp = httpx.get(f"https://clob.polymarket.com/book?token_id={tid}")
                    print(f"Candidate: {m['question'][:40]} | P:{mid:.3f} | S:{s:.3f} | CLOB Status: {resp.status_code}")
                    if resp.status_code == 200:
                        book = resp.json()
                        print(f"  CLOB Asks: {len(book.get('asks', []))}")

if __name__ == "__main__":
    find_perfect_candidate()
