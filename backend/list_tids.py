import requests
import json

def get_list():
    url = "https://gamma-api.polymarket.com/markets?limit=100&active=true&closed=false"
    r = requests.get(url)
    data = r.json()
    count = 0
    for m in data:
        tids = m.get("clobTokenIds")
        if tids:
            if isinstance(tids, str): tids = json.loads(tids)
            q = m.get("question")
            # print(f"{q[:40]}... | {tids[0]}")
            count += 1
            # Just pick one market that looks interesting - usually sports or politics
            if "Trump" in q or "Bitcoin" in q or "NBA" in q:
                 print(f"MATCH: {q} | TID: {tids[0]}")
    if count == 0:
        print("No CLOB token IDs found in top 100 markets.")

if __name__ == "__main__":
    get_list()
