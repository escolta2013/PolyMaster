import requests
import json

def test_data_api_trades():
    # High volume market token (Super Bowl)
    token_id = "423349548502197541952412480031728896145392673031415571339"
    url = "https://data-api.polymarket.com/trades"
    params = {"asset_id": token_id, "limit": 10}
    
    print(f"Testing Data API: {url} for asset_id: {token_id}")
    try:
        r = requests.get(url, params=params, timeout=10)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            trades = r.json()
            if trades:
                print(f"SUCCESS|Found {len(trades)} trades")
                print(f"Sample Trade: {json.dumps(trades[0], indent=2)}")
            else:
                print("EMPTY|Data API returned no trades")
        else:
            print(f"Error Body: {r.text}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_data_api_trades()
