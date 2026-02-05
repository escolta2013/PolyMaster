import requests
import json

def analyze_top_market():
    # Search for Bitcoin related markets (usually highest volume)
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "active": "true",
        "closed": "false",
        "order": "volume",
        "ascending": "false",
        "limit": 10,
        "search": "Bitcoin"
    }
    r = requests.get(url, params=params)
    markets = r.json()
    
    if not markets:
        print("NO_BITCOIN_MARKETS_FOUND")
        return

    m = markets[0]
    print(f"MARKET|{m.get('question')}")
    print(f"ID|{m.get('id')}")
    print(f"CONDITION_ID|{m.get('conditionId')}")
    print(f"CLOB_TOKEN_IDS|{m.get('clobTokenIds')}")
    print(f"REWARDS|{m.get('rewards')}")
    
    # Check if tokens field exists
    if "tokens" in m:
        print(f"TOKENS_FIELD|{json.dumps(m['tokens'])}")

if __name__ == "__main__":
    analyze_top_market()
