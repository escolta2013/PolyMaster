import requests
import json

def get_trending():
    url = "https://gamma-api.polymarket.com/events?limit=5&active=true&order=volume&ascending=false"
    r = requests.get(url)
    events = r.json()
    for e in events:
        print(f"EVENT: {e.get('title')}")
        markets = e.get("markets", [])
        for m in markets:
            tids = m.get("clobTokenIds")
            if tids:
                tid = json.loads(tids)[0] if isinstance(tids, str) else tids[0]
                bur = requests.get(f"https://clob.polymarket.com/book?token_id={tid}")
                if bur.status_code == 200:
                    ob = bur.json()
                    ask = float(ob["asks"][0]["price"]) if ob.get("asks") else 1.0
                    bid = float(ob["bids"][0]["price"]) if ob.get("bids") else 0.0
                    print(f"  Q: {m.get('question')[:40]} | P: {(ask+bid)/2:.3f} | S: {ask-bid:.3f} | TID: {tid}")

if __name__ == "__main__":
    get_trending()
