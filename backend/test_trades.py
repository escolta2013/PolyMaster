import os
import sys
import json
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from app.engines.tracker.clob_client import ClobClient

def test_specific_token(token_id):
    clob = ClobClient()
    print(f"Testing Token ID: {token_id}")
    try:
        trades = clob.get_market_trades(token_id)
        if trades:
            print(f"SUCCESS|Found {len(trades)} trades")
            for i, t in enumerate(trades[:3]):
                maker = t.get('maker_address', 'N/A')
                taker = t.get('taker_address', 'N/A')
                print(f"TRADE {i}|Maker: {maker}|Taker: {taker}|Price: {t.get('price')}|Size: {t.get('size')}")
        else:
            print("EMPTY|No trades found for this token")
    except Exception as e:
        print(f"ERROR|{str(e)}")

if __name__ == "__main__":
    # Using the token ID for "Will the Arizona Cardinals win Super Bowl 2026?" (High Volume)
    target_token = "423349548502197541952412480031728896145392673031415571339"
    test_specific_token(target_token)
