import os
import requests
from dotenv import load_dotenv
from py_clob_client.client import ClobClient

load_dotenv()

def verify():
    print("Checking CLOB connectivity...")
    host = "https://clob.polymarket.com"
    
    # 1. Direct Request
    try:
        print(f"\n1. Direct GET {host}/sampling-markets")
        r = requests.get(f"{host}/sampling-markets", timeout=10)
        print(f"Status Code: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"Found {len(data)} items in sampling-markets")
    except Exception as e:
        print(f"Direct request failed: {e}")

    # 2. SDK Request
    try:
        print(f"\n2. SDK get_markets()")
        client = ClobClient(host, chain_id=137)
        markets = client.get_markets()
        print(f"SDK found {len(markets)} markets")
        if markets:
            m = markets[0]
            print(f"Market Object Type: {type(m)}")
            # Print attributes to see how to access data
            print(f"Available attributes: {[attr for attr in dir(m) if not attr.startswith('_')]}")
            
            # Common attributes in OpenOrder entities
            for attr in ['question', 'condition_id', 'market_id', 'id', 'ticker']:
                if hasattr(m, attr):
                    print(f" - {attr}: {getattr(m, attr)}")
    except Exception as e:
        print(f"SDK request failed: {e}")

if __name__ == "__main__":
    verify()
