import sys
import os
import json

# Add backend to path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.client import PolyClient

def inspect():
    client = PolyClient.get_instance()
    print("Fetching simplified markets...")
    
    # Try get_sampling_simplified_markets if available (common in py-clob-client)
    try:
        markets = client.get_sampling_simplified_markets(next_cursor="")
        print(f"Got response type: {type(markets)}")
        
        # Depending on version, it might return a dict with 'data' or a list
        data = markets.get('data') if isinstance(markets, dict) else markets
        
        print(f"Found {len(data)} markets.")
        if len(data) > 0:
            print("Sample Market:")
            print(json.dumps(data[0], indent=2, default=str))
            
    except Exception as e:
        print(f"Error fetching sampling: {e}")
        # Fallback to standard get_markets which is heavier but reliable
        try:
             print("Fallback: Validating get_markets...")
             mkts = client.get_markets(next_cursor="")
             print(f"Found {len(mkts.get('data', []))} markets (standard API).")
        except Exception as e2:
             print(f"Fallback failed: {e2}")

if __name__ == "__main__":
    inspect()
