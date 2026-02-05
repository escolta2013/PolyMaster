import requests
import json

def get_active_market():
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "active": "true",
        "closed": "false",
        "order": "volume",
        "ascending": "false",
        "limit": 5
    }
    r = requests.get(url, params=params)
    markets = r.json()
    
    for m in markets:
        vol = float(m.get("volume", 0))
        if vol > 0:
            tokens = m.get("clobTokenIds")
            if tokens:
                if isinstance(tokens, str):
                    tokens = json.loads(tokens)
                print(f"MARKET_FOUND|{m.get('id')}|{m.get('question')}|{vol}|{json.dumps(tokens)}")
                return
    print("NO_ACTIVE_MARKETS_WITH_VOLUME")

if __name__ == "__main__":
    get_active_market()
