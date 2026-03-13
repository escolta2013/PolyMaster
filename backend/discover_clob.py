
import httpx
import json

def list_clob_markets():
    try:
        # Try different CLOB endpoints
        base = "https://clob.polymarket.com"
        r = httpx.get(f"{base}/markets")
        print(f"CLOB /markets Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                print(f"Total Markets in list: {len(data)}")
                if data:
                    print(f"Sample Item: {data[0]}")
            elif isinstance(data, dict):
                print(f"Keys in data: {data.keys()}")
                if 'data' in data:
                    print(f"Total in 'data': {len(data['data'])}")

        # Try /sampling (usually returns active markets)
        r = httpx.get(f"{base}/sampling")
        print(f"\nCLOB /sampling Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"Total sampled tokens: {len(data)}")
            if data:
                print(f"Sample token: {data[0]}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_clob_markets()
