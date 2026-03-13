import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging to see SDK internals
logging.basicConfig(level=logging.INFO)

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from app.engines.tracker.clob_client import ClobClient
from py_clob_client.clob_types import TradeParams

def verify_derivation():
    print("Initializing ClobClient...")
    clob = ClobClient()
    
    if hasattr(clob.sdk_client, 'api_key'):
        print(f"L2 Credentials Derived Successfully: {clob.sdk_client.api_key[:10]}...")
    else:
        print("L2 Credentials NOT FOUND in SDK client")

    # Try a market that is definitely active - let's find it from Gamma again
    import requests
    r = requests.get("https://gamma-api.polymarket.com/markets?active=true&closed=false&order=volume&ascending=false&limit=1")
    m = r.json()[0]
    token_id = json.loads(m['clobTokenIds'])[0]
    print(f"Testing definitely active market: {m.get('question')} (Token: {token_id})")
    
    try:
        params = TradeParams(market=token_id)
        trades = clob.sdk_client.get_trades(params)
        t_list = list(trades)
        if t_list:
            print(f"SUCCESS|Found {len(t_list)} trades")
            print(f"Trade Data: {vars(t_list[0])}")
        else:
            print("EMPTY|No trades found even for top market")
    except Exception as e:
        print(f"ERROR|{e}")

if __name__ == "__main__":
    import json
    verify_derivation()
