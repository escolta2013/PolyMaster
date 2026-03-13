import os
import sys
import json
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from app.engines.tracker.clob_client import ClobClient
from py_clob_client.clob_types import TradeParams

def test_multiple_tokens():
    clob = ClobClient()
    
    # Selection of tokens from sampling-markets
    tokens = [
        # Texas Senate Yes
        "21265207456609426291246075480390336499088453711419597084147957999650569091884",
        # Scott Wiener Yes
        "70118895962676917756299751698352496946996500581707013323004777630737006170068",
        # Norway gold medals Yes
        "37951513621735784471651257045517975893424565554701830077103055531806326097100"
    ]
    
    for token_id in tokens:
        print(f"\nTesting Token: {token_id}")
        try:
            params = TradeParams(market=token_id)
            trades = clob.sdk_client.get_trades(params)
            t_list = list(trades)
            if t_list:
                print(f"SUCCESS|Found {len(t_list)} trades")
                t = t_list[0]
                # Check for wallet addresses
                maker = getattr(t, 'maker_address', 'N/A')
                taker = getattr(t, 'taker_address', 'N/A')
                print(f"Sample Trade: Maker={maker}, Taker={taker}, Price={getattr(t, 'price', 'N/A')}")
                if maker != 'N/A' or taker != 'N/A':
                    print("!!! AUTHENTICATED WALLET DATA DETECTED !!!")
            else:
                print("EMPTY|No trades found")
        except Exception as e:
            print(f"ERROR|{e}")

if __name__ == "__main__":
    test_multiple_tokens()
