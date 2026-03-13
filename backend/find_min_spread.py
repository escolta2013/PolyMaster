
import httpx
import json

def find_min_spread():
    r = httpx.get('https://gamma-api.polymarket.com/markets?limit=100&order=volume&ascending=false&active=true&closed=false')
    markets = r.json()
    print(f"Checking {len(markets)} markets...")
    
    valid_prices = []
    for m in markets:
        bid = m.get('bestBid')
        ask = m.get('bestAsk')
        spread = m.get('spread')
        
        if bid is not None and ask is not None:
            b = float(bid)
            a = float(ask)
            s = float(spread) if spread is not None else (a - b)
            valid_prices.append((s, m['question'], b, a))
            
    valid_prices.sort()
    print("\nTop 10 Markets by Lowest Spread:")
    for s, q, b, a in valid_prices[:10]:
        print(f"Spread: {s:.4f} | B:{b:.3f} A:{a:.3f} | {q[:50]}")

if __name__ == "__main__":
    find_min_spread()
