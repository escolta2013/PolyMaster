import requests
import json

url = "https://gamma-api.polymarket.com/markets?limit=10&active=true&closed=false&query=NBA"
r = requests.get(url)
for m in r.json():
    print(f"Q: {m.get('question')[:60]}")
    tids = m.get("clobTokenIds")
    if tids:
        tid = json.loads(tids)[0] if isinstance(tids, str) else tids[0]
        # Check price
        bur = requests.get(f"https://clob.polymarket.com/book?token_id={tid}")
        if bur.status_code == 200:
            ob = bur.json()
            if ob.get("asks") and ob.get("bids"):
                ask = float(ob["asks"][0]["price"])
                bid = float(ob["bids"][0]["price"])
                print(f"  P: {(ask+bid)/2:.3f} | S: {ask-bid:.3f}")
            else:
                print("  No liquidity")
