import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from app.engines.tracker.clob_client import ClobClient
from py_clob_client.clob_types import TradeParams

def debug_trades():
    clob = ClobClient()
    # High volume token ID
    token_id = "423349548502197541952412480031728896145392673031415571339"
    print(f"Testing market: {token_id}")
    
    try:
        params = TradeParams(market=token_id)
        trades = clob.sdk_client.get_trades(params)
        trades_list = list(trades)
        
        if trades_list:
            print(f"SUCCESS|Found {len(trades_list)} trades")
            t = trades_list[0]
            print(f"Trade Data (repr): {repr(t)}")
            print(f"Trade Data (dict): {getattr(t, '__dict__', 'No __dict__')}")
            
            # Check fields manually
            fields = ['maker_address', 'taker_address', 'price', 'size', 'side', 'maker_order_id', 'taker_order_id']
            for f in fields:
                val = getattr(t, f, 'MISSING')
                print(f"  {f}: {val}")
        else:
            print("EMPTY|Still no trades found")
            
    except Exception as e:
        print(f"ERROR|{e}")

if __name__ == "__main__":
    debug_trades()
