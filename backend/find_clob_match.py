import requests
import json

def find_clob_match():
    url = "https://clob.polymarket.com/markets"
    r = requests.get(url)
    markets = r.json()
    
    if isinstance(markets, dict):
        markets = markets.get("data", [])

    print(f"Checking {len(markets)} CLOB markets for liquidity...")
    
    matches = []
    for i, m in enumerate(markets[:500]):
        description = m.get("description", "No Description")
        tokens = m.get("tokens", [])
        
        for t in tokens:
            tid = t.get("token_id")
            outcome = t.get("outcome")
            if not tid: continue
            
            try:
                book_url = f"https://clob.polymarket.com/book?token_id={tid}"
                br = requests.get(book_url, timeout=2)
                if br.status_code == 200:
                    ob = br.json()
                    asks = ob.get("asks", [])
                    bids = ob.get("bids", [])
                    if asks and bids:
                        ask = float(asks[0]["price"])
                        bid = float(bids[0]["price"])
                        mid = (ask+bid)/2
                        spread = ask-bid
                        if 0.35 <= mid <= 0.65 and spread <= 0.25:
                            print(f"\nMatch Found!")
                            print(f"Q: {description} ({outcome})")
                            print(f"TID: {tid}")
                            print(f"P: {mid:.3f} | S: {spread:.3f}")
                            matches.append({"tid": tid, "mid": mid, "spread": spread, "name": description, "outcome": outcome})
                            if len(matches) >= 3: return matches
            except: continue
    print("Done")
    return matches

if __name__ == "__main__":
    find_clob_match()
