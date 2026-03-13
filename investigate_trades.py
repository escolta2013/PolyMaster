import httpx
import json

print("=" * 80)
print("INVESTIGANDO LOS 4 TRADES")
print("=" * 80)

# Los 4 trades según copy_trades
trades = [
    {
        "name": "Giannis Antetokounmpo NOT traded",
        "market_id": "0xd6ea801f468ac357fa3c32d2ceeeb863a0fcb0e44ef66082558c69fb803116c2",
        "outcome": "No",
        "bought_at": 0.51,
        "shares": 39.22,
        "invested": 20,
        "timestamp": "2026-02-17 20:07:32"
    },
    {
        "name": "A House of Dynamite - Best Picture",
        "market_id": "0x4abbda1f1f5b6789342919e1db7ee99cc251d153d3661580ac8d9bc3e472a070",
        "outcome": "Yes",
        "bought_at": 0.51,
        "shares": 39.22,
        "invested": 20,
        "timestamp": "2026-02-17 21:15:28"
    },
    {
        "name": "No Other Choice - Best Picture",
        "market_id": "0x476a2f8af724a61185b127db68d0b54046db5bb7aa690d6f8c5d623a0472e77f",
        "outcome": "Yes",
        "bought_at": 0.51,
        "shares": 39.22,
        "invested": 20,
        "timestamp": "2026-02-17 21:15:56"
    },
    {
        "name": "Ken Paxton - Texas Primary",
        "market_id": "0x99a0fdc1bb6308873bf87eb75a47e21c8340fe20fb6b033444c1d21392da10a9",
        "outcome": "Yes",
        "bought_at": 0.745,
        "shares": 26.85,
        "invested": 20,
        "timestamp": "2026-02-17 21:42:40"
    }
]

for i, trade in enumerate(trades, 1):
    print(f"\n{'='*80}")
    print(f"TRADE #{i}: {trade['name']}")
    print(f"{'='*80}")
    print(f"Timestamp: {trade['timestamp']}")
    print(f"Market ID: {trade['market_id']}")
    print(f"Outcome Bought: {trade['outcome']}")
    print(f"Price Bought: ${trade['bought_at']:.3f}")
    print(f"Shares: {trade['shares']:.2f}")
    print(f"Invested: ${trade['invested']:.2f}")
    
    # Try to get market info from Gamma API
    try:
        # First, try to get market details using the condition_id (market_id)
        # Gamma API uses different endpoints
        response = httpx.get(
            f"https://gamma-api.polymarket.com/markets",
            params={"condition_id": trade['market_id']},
            timeout=10
        )
        
        if response.status_code == 200:
            markets_data = response.json()
            if markets_data:
                market = markets_data[0] if isinstance(markets_data, list) else markets_data
                print(f"\n📊 Market Info:")
                print(f"  Question: {market.get('question', 'N/A')}")
                print(f"  Active: {market.get('active', 'N/A')}")
                print(f"  Closed: {market.get('closed', 'N/A')}")
                print(f"  End Date: {market.get('end_date_iso', 'N/A')}")
                
                # Get token IDs
                tokens = market.get('tokens', [])
                if tokens:
                    print(f"\n  Tokens:")
                    for token in tokens:
                        outcome_label = token.get('outcome', 'Unknown')
                        token_id = token.get('token_id', 'N/A')
                        print(f"    {outcome_label}: {token_id}")
                        
                        # If this is the outcome we bought, get its current price
                        if outcome_label.lower() == trade['outcome'].lower():
                            try:
                                price_resp = httpx.get(
                                    f"https://clob.polymarket.com/midpoint",
                                    params={"token_id": token_id},
                                    timeout=5
                                )
                                if price_resp.status_code == 200:
                                    price_data = price_resp.json()
                                    current_price = float(price_data.get('mid', 0))
                                    
                                    current_value = trade['shares'] * current_price
                                    pnl = current_value - trade['invested']
                                    pnl_pct = (pnl / trade['invested']) * 100
                                    
                                    print(f"\n💰 Current Status:")
                                    print(f"  Current Price: ${current_price:.3f}")
                                    print(f"  Current Value: ${current_value:.2f}")
                                    print(f"  P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%)")
                                    
                                    if pnl > 0:
                                        print(f"  Status: ✅ WINNING")
                                    elif pnl < 0:
                                        print(f"  Status: ❌ LOSING")
                                    else:
                                        print(f"  Status: ⚖️ BREAK-EVEN")
                            except Exception as e:
                                print(f"  ⚠️ Could not fetch current price: {e}")
        else:
            print(f"⚠️ Could not fetch market info (status {response.status_code})")
            
    except Exception as e:
        print(f"❌ Error: {e}")

print(f"\n{'='*80}")
print("END OF INVESTIGATION")
print(f"{'='*80}")
