import os
import sys
import json
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from app.engines.tracker.clob_client import ClobClient

def test_orderbook(token_id):
    clob = ClobClient()
    print(f"Testing Orderbook for Token ID: {token_id}")
    try:
        book = clob.get_orderbook(token_id)
        if book.get("bids") or book.get("asks"):
            print(f"SUCCESS|Found {len(book.get('bids', []))} bids and {len(book.get('asks', []))} asks")
            if book.get("bids"):
                print(f"Top Bid: {book['bids'][0]}")
        else:
            print("EMPTY|Orderbook is empty")
    except Exception as e:
        print(f"ERROR|{str(e)}")

if __name__ == "__main__":
    target_token = "423349548502197541952412480031728896145392673031415571339"
    test_orderbook(target_token)
