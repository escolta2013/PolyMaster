import requests
import json
import sys

def go():
    res = requests.get("https://gamma-api.polymarket.com/events?slug=how-long-will-the-state-of-the-union-address-be")
    for e in res.json():
        for m in e.get("markets", []):
            try:
                tids = json.loads(m.get('clobTokenIds', '[]'))
            except:
                tids = []
            tid = tids[0] if tids else "NO_TID"
            print(f"[{tid}] {m.get('question')} | Active: {m.get('active')} | Closed: {m.get('closed')}")
            
if __name__ == "__main__":
    go()
