import requests
import json

def get_list():
    url = "https://gamma-api.polymarket.com/markets?limit=10&active=true&closed=false&query=market%20cap"
    r = requests.get(url)
    data = r.json()
    for m in data:
        tids_raw = m.get("clobTokenIds")
        if tids_raw:
            tids = json.loads(tids_raw) if isinstance(tids_raw, str) else tids_raw
            if tids:
                q = m.get("question")
                tid = tids[0]
                bur = requests.get(f"https://clob.polymarket.com/book?token_id={tid}")
                if bur.status_code == 200:
                    ob = bur.json()
                    if ob.get("asks") and ob.get("bids"):
                         ask = float(ob["asks"][0]["price"])
                         bid = float(ob["bids"][0]["price"])
                         print(f"Q: {q} | P: {(ask+bid)/2:.3f} | S: {ask-bid:.3f} | TID: {tid}")

if __name__ == "__main__":
    get_list()
