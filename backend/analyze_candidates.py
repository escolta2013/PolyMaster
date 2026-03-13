
import httpx
import json

def analyze_calibration_candidates():
    r = httpx.get('https://gamma-api.polymarket.com/markets?limit=300&order=volume&ascending=false&active=true&closed=false')
    markets = r.json()
    
    candidates = []
    for m in markets:
        bid = m.get('bestBid')
        ask = m.get('bestAsk')
        
        if bid is not None and ask is not None:
            b, a = float(bid), float(ask)
            mid = (a + b) / 2
            if 0.1 <= mid <= 0.9:
                s = float(m.get('spread') or (a - b))
                candidates.append((s, mid, m['question']))
    
    candidates.sort() # Sort by spread
    print(f"Found {len(candidates)} markets in price range 0.1 - 0.9")
    print("\nTop 15 Candidates by Spread:")
    for s, mid, q in candidates[:15]:
        print(f"Spread: {s:.3f} | Price: {mid:.3f} | {q[:60]}")

if __name__ == "__main__":
    analyze_calibration_candidates()
