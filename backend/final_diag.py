import os
import sys
import json
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from app.engines.tracker.clob_client import ClobClient

def final_diag():
    clob = ClobClient()
    print("Fetching markets from CLOB SDK...")
    try:
        # Try to get sampling markets as it's often more informative
        try:
            sampling = clob.sdk_client.get_sampling_markets()
            print(f"Sampling markets found: {len(sampling)}")
            if sampling:
                print(f"Sample data structure: {json.dumps(sampling[0], indent=2)}")
        except:
            print("get_sampling_markets failed")

        markets = clob.sdk_client.get_markets()
        print(f"\nFound {len(markets)} markets in get_markets()")
        
        if markets:
            m = markets[0]
            print(f"Object type: {type(m)}")
            try:
                # Some SDK objects use __dict__
                print(f"Attributes (__dict__): {json.dumps(m.__dict__, indent=2, default=str)}")
            except:
                # Others are Pydantic models or slots
                print(f"Attributes (dir): {[a for a in dir(m) if not a.startswith('_')]}")
                
    except Exception as e:
        print(f"Diagnostic failed: {e}")

if __name__ == "__main__":
    final_diag()
