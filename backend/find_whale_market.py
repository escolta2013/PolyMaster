import requests
import json

def find_high_volume():
    url = "https://gamma-api.polymarket.com/events"
    params = {
        "closed": "false",
        "order": "volume",
        "ascending": "false",
        "limit": 10
    }
    r = requests.get(url, params=params)
    events = r.json()
    
    for e in events:
        vol = float(e.get("volume", 0))
        print(f"EVENT|{e.get('title')}|Vol: ${vol:,.0f}")
        if vol > 100000: # Over $100k
            # Get first market of this event
            markets = e.get("markets", [])
            if markets:
                m = markets[0]
                tokens = m.get("clobTokenIds")
                if tokens:
                    if isinstance(tokens, str):
                        tokens = json.loads(tokens)
                    print(f"TARGET_MARKET|{m.get('question')}|Token: {tokens[0]}")
                    return tokens[0]
    return None

if __name__ == "__main__":
    find_high_volume()
