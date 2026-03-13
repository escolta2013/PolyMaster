import requests
import json

def find_liquid():
    # Fetch from Gamma 'all' active
    url = "https://gamma-api.polymarket.com/markets?limit=100&active=true&closed=false"
    r = requests.get(url)
    data = r.json()
    for m in data:
        tids_raw = m.get("clobTokenIds")
        if not tids_raw: continue
        tids = json.loads(tids_raw) if isinstance(tids_raw, str) else tids_raw
        if not tids: continue
        tid = tids[0]
        try:
            bur = requests.get(f"https://clob.polymarket.com/book?token_id={tid}", timeout=2)
            if bur.status_code == 200:
                ob = bur.json()
                if ob.get("asks") and ob.get("bids"):
                    ask = float(ob["asks"][0]["price"])
                    bid = float(ob["bids"][0]["price"])
                    mid = (ask+bid)/2
                    spr = ask-bid
                    if 0.10 < mid < 0.90 and (spr < 0.15 or (spr < 0.25 and "Election" in m.get("question", ""))):
                         print(f"[{tid}] {m.get('question')[:50]} | P:{mid:.3f} | S:{spr:.3f}")
        except: pass

if __name__ == "__main__":
    find_liquid()
