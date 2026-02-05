
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import RequestArgs

def test_sdk_no_auth():
    print("Initializing ClobClient (No Auth)...")
    # Public host for Polymarket CLOB
    host = "https://clob.polymarket.com"
    chain_id = 137 # Polygon

    try:
        client = ClobClient(host, chain_id=chain_id)
        print("Client initialized.")
    except Exception as e:
        print(f"Failed to init client: {e}")
        return

    # 1. Try fetching Orderbook (known public)
    # Using a token_id found in previous logs
    token_id = "37747499400698142913115558953999479139544929542228542782146153630812707498225" 
    
    try:
        print(f"Fetching Orderbook for {token_id}...")
        ob = client.get_order_book(token_id)
        print(f"Orderbook Result: {ob}")
    except Exception as e:
        print(f"Orderbook fetch failed: {e}")

    # 2. Try fetching Trades (failed with 401 via requests)
    try:
        print(f"Fetching Trades for {token_id}...")
        # Note: function name might be get_trades or get_last_trades depending on version
        # Checking commonly used methods
        if hasattr(client, "get_trades"):
            from py_clob_client.clob_types import TradeParams
            try:
                # Based on TradeParams definition (maker_address, taker_address, market)
                # usage: client.get_trades(TradeParams(market=token_id))
                params = TradeParams(market=token_id)
                trades = client.get_trades(params=params)
                print(f"Trades Result: {trades}")
            except Exception as e:
                print(f"TradeParams usage failed: {e}")
                
        elif hasattr(client, "get_last_trade_price"):
             price = client.get_last_trade_price(token_id)
             print(f"Last Price Result: {price}")
        else:
             print("Could not find get_trades method on client.")
             print(dir(client))

    except Exception as e:
        print(f"Trades fetch failed: {e}")

if __name__ == "__main__":
    test_sdk_no_auth()
