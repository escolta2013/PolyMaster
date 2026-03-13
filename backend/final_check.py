import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from app.engines.tracker.clob_client import ClobClient
from py_clob_client.clob_types import TradeParams

def final_attempt():
    clob = ClobClient()
    print("Listing markets from CLOB SDK...")
    try:
        markets = clob.sdk_client.get_markets()
        print(f"Found {len(markets)} markets\n")
        
        for i, m in enumerate(markets):
            # Print whatever attributes are available
            print(f"Market {i}:")
            attrs = [a for a in dir(m) if not a.startswith('_')]
            for attr in attrs:
                try:
                    val = getattr(m, attr)
                    if not callable(val):
                        print(f"  - {attr}: {val}")
                except:
                    pass
            
            # Use market_id or condition_id to get trades
            market_id = getattr(m, 'market_id', None)
            if not market_id:
                # Try getting it from the object itself if it's a dict-like or other attribute
                market_id = getattr(m, 'id', None)
            
            if market_id:
                print(f"  Attempting trades for: {market_id}")
                try:
                    params = TradeParams(market=market_id)
                    trades = clob.sdk_client.get_trades(params)
                    t_list = list(trades)
                    if t_list:
                        print(f"  SUCCESS|Found {len(t_list)} trades")
                        t = t_list[0]
                        print(f"  Sample Trade: {dir(t)}")
                        # Print relevant trade info
                        for t_attr in ['maker_address', 'taker_address', 'price', 'size', 'side']:
                            if hasattr(t, t_attr):
                                print(f"    {t_attr}: {getattr(t, t_attr)}")
                    else:
                        print("  EMPTY|No trades found")
                except Exception as te:
                    print(f"  Trade fetch error: {te}")
            print("-" * 30)
            
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    final_attempt()
