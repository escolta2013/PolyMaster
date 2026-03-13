import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

def get_sampling_raw():
    host = "https://clob.polymarket.com"
    print(f"Fetching {host}/sampling-markets")
    try:
        r = requests.get(f"{host}/sampling-markets", timeout=10)
        if r.status_code == 200:
            data = r.json()
            print(f"RAW SAMPLING (First 4):")
            import json
            print(json.dumps(data, indent=2))
        else:
            print(f"Bad status: {r.status_code}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    get_sampling_raw()
