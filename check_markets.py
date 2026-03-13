import httpx
import json

# Market IDs from the 4 trades
markets = {
    "Giannis NO Trade": "0xd6ea801f468ac357fa3c32d2ceeeb863a0fcb0e44ef66082558c69fb803116c2",
    "A House of Dynamite": "0x4abbda1f1f5b6789342919e1db7ee99cc251d153d3661580ac8d9bc3e472a070",
    "No Other Choice": "0x476a2f8af724a61185b127db68d0b54046db5bb7aa690d6f8c5d623a0472e77f",
    "Ken Paxton": "0x99a0fdc1bb6308873bf87eb75a47e21c8340fe20fb6b033444c1d21392da10a9"
}

# Trade details
trades = {
    "Giannis NO Trade": {"bought_at": 0.51, "shares": 39.22, "invested": 20, "side": "NO"},
    "A House of Dynamite": {"bought_at": 0.51, "shares": 39.22, "invested": 20, "side": "YES"},
    "No Other Choice": {"bought_at": 0.51, "shares": 39.22, "invested": 20, "side": "YES"},
    "Ken Paxton": {"bought_at": 0.745, "shares": 26.85, "invested": 20, "side": "YES"}
}

print("=" * 80)
print("POLYMASTER TRADE PERFORMANCE CHECK")
print("=" * 80)

total_invested = 0
total_current_value = 0

for name, token_id in markets.items():
    print(f"\n📊 {name}")
    print("-" * 80)
    
    try:
        # Get current midpoint price
        response = httpx.get(f"https://clob.polymarket.com/midpoint?token_id={token_id}", timeout=10)
        data = response.json()
        
        current_price = float(data.get("mid", 0))
        
        trade = trades[name]
        bought_at = trade["bought_at"]
        shares = trade["shares"]
        invested = trade["invested"]
        side = trade["side"]
        
        # Calculate current value
        current_value = shares * current_price
        pnl = current_value - invested
        pnl_pct = (pnl / invested) * 100
        
        total_invested += invested
        total_current_value += current_value
        
        print(f"  Side: {side}")
        print(f"  Bought at: ${bought_at:.3f}")
        print(f"  Current Price: ${current_price:.3f}")
        print(f"  Shares: {shares:.2f}")
        print(f"  Invested: ${invested:.2f}")
        print(f"  Current Value: ${current_value:.2f}")
        print(f"  P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%)")
        
        if pnl > 0:
            print(f"  Status: ✅ WINNING")
        elif pnl < 0:
            print(f"  Status: ❌ LOSING")
        else:
            print(f"  Status: ⚖️ BREAK-EVEN")
            
    except Exception as e:
        print(f"  ❌ Error fetching data: {e}")

print("\n" + "=" * 80)
print("PORTFOLIO SUMMARY")
print("=" * 80)
total_pnl = total_current_value - total_invested
total_pnl_pct = (total_pnl / total_invested) * 100 if total_invested > 0 else 0

print(f"Total Invested: ${total_invested:.2f}")
print(f"Current Value: ${total_current_value:.2f}")
print(f"Total P&L: ${total_pnl:+.2f} ({total_pnl_pct:+.1f}%)")
print("=" * 80)
