import requests
import json

def search_sotu():
    url = "https://gamma-api.polymarket.com/markets?query=State%20of%20the%20Union&active=true"
    r = requests.get(url)
    data = r.json()
    for m in data:
        print(f"Q: {m.get('question')} | ID: {m.get('id')}")
        tids = m.get("clobTokenIds")
        if tids:
            print(f"  TIDs: {tids}")
            print(f"  Outcomes: {m.get('outcomes')}")

if __name__ == "__main__":
    search_sotu()
