import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

def analyze_positions():
    # Use one of the whale addresses found earlier
    whale_address = "0x7e279561b5766f199a34f596da04d9c3783e178d"
    url = "https://data-api.polymarket.com/positions"
    params = {"user": whale_address}
    
    print(f"Analyzing positions for whale: {whale_address}")
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            positions = r.json()
            if positions:
                print(f"Total positions: {len(positions)}")
                print(f"Sample Position Structure (First one):")
                print(json.dumps(positions[0], indent=2))
                
                # Analyze common fields across positions
                all_keys = set()
                for p in positions[:10]:
                    all_keys.update(p.keys())
                print(f"\nCommon keys in positions: {all_keys}")
            else:
                print("No positions found for this whale.")
        else:
            print(f"Error fetching positions: {r.status_code}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    analyze_positions()
