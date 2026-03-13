import requests
import json

def get_tid():
    slug = "how-long-will-the-state-of-the-union-address-be"
    url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
    r = requests.get(url)
    data = r.json()
    for m in data:
        print(f"Q: {m.get('question')}")
        tids_raw = m.get("clobTokenIds")
        if tids_raw:
            tids = json.loads(tids_raw) if isinstance(tids_raw, str) else tids_raw
            outcomes_raw = m.get("outcomes")
            outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
            
            for i, outcome in enumerate(outcomes):
                print(f"  Outcome: {outcome} | TID: {tids[i]}")

if __name__ == "__main__":
    get_tid()
