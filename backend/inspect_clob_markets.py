import os
import sys
import json
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from app.engines.tracker.clob_client import ClobClient
from py_clob_client.clob_types import TradeParams

def inspect_clob_markets():
    clob = ClobClient()
    print("Fetching markets from CLOB SDK...")
    try:
        # get_markets() returns a list of OpenOrder entities
        markets = clob.sdk_client.get_markets()
        print(f"Found {len(markets)} markets in CLOB\n")
        
        for i, m in enumerate(markets):
            # Print all interesting fields
            q = getattr(m, 'question', 'No Question')
            c_id = getattr(m, 'condition_id', 'No Condition ID')
            m_id = getattr(m, 'market_id', 'No Market ID')
            print(f"[{i}] Question: {q}")
            print(f"    Condition ID: {c_id}")
            print(f"    Market ID: {m_id}")
            
            # Try to get trades for this market
            try:
                # We need a token ID. Usually markets have multiple tokens (Yes/No).
                # Let's try to get tokens for this market.
                # In many SDK versions, we might need to get sampling to see current tokens.
                print(f"    Testing trades for market_id: {m_id}")
                params = TradeParams(market=m_id)
                trades = clob.sdk_client.get_trades(params)
                if trades:
                    print(f"    SUCCESS|Found {len(list(trades))} trades")
                    first_trade = list(trades)[0]
                    # Check for wallet addresses
                    # SDK Trade objects might have taker/maker
                    # Let's see what's inside
                    print(f"    Trade Sample keys: {dir(first_trade)}")
                    if hasattr(first_trade, 'maker_address'):
                        print(f"    Maker: {first_trade.maker_address}")
                    if hasattr(first_trade, 'taker_address'):
                        print(f"    Taker: {first_trade.taker_address}")
                else:
                    print("    EMPTY|No trades found")
            except Exception as trade_e:
                print(f"    Trade fetch failed: {trade_e}")
            print("-" * 40)
            
    except Exception as e:
        print(f"Market fetch failed: {e}")

if __name__ == "__main__":
    inspect_clob_markets()
