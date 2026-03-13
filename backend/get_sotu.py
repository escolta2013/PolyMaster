import requests
import json

def get_trending():
    url = "https://gamma-api.polymarket.com/events?limit=20&active=true&order=volume&ascending=false"
    r = requests.get(url)
    events = r.json()
    for e in events:
        if "State of the Union" in e.get('title', ''):
            print(f"EVENT: {e.get('title')}")
            markets = e.get("markets", [])
            for m in markets:
                q = m.get('question')
                if "100" in q or True:
                    tids = m.get("clobTokenIds")
                    if tids:
                        tid = json.loads(tids)[0] if isinstance(tids, str) else tids[0]
                        bur = requests.get(f"https://clob.polymarket.com/book?token_id={tid}")
                        if bur.status_code == 200:
                            ob = bur.json()
                            ask = float(ob["asks"][0]["price"]) if ob.get("asks") else None
                            bid = float(ob["bids"][0]["price"]) if ob.get("bids") else None
                            if ask is not None and bid is not None:
                                mid = (ask+bid)/2
                                spr = ask-bid
                                print(f"  Q: {q[:40]} | P: {mid:.3f} | S: {spr:.3f} | TID: {tid}")

if __name__ == "__main__":
    get_trending()
