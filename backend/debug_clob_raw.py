
import httpx
import json

def find_active_markets():
    # Fetch from CLOB directly
    r = httpx.get("https://clob.polymarket.com/markets")
    markets = r.json()
    print(f"Total CLOB Markets: {len(markets)}")
    
    # Sort by volume or something if possible, but the API might not support it well
    # Just take the first few that look like real markets
    count = 0
    for m in markets:
        if m.get('active') and not m.get('closed'):
            print(f"\nMarket: {m.get('question')}")
            print(f"Condition ID: {m.get('condition_id')}")
            tids = m.get('tokens', [])
            for t in tids:
                tid = t.get('token_id')
                # Fetch book
                book_resp = httpx.get(f"https://clob.polymarket.com/book?token_id={tid}")
                if book_resp.status_code == 200:
                    book = book_resp.json()
                    bids = book.get('bids', [])
                    asks = book.get('asks', [])
                    print(f"  Token: {t.get('outcome')} ({tid})")
                    print(f"  Bids: {len(bids)} | Asks: {len(asks)}")
                    if bids: print(f"    Best Bid: {bids[0]}")
                    if asks: print(f"    Best Ask: {asks[0]}")
                else:
                    print(f"  Token: {t.get('outcome')} - Error fetching book: {book_resp.status_code}")
            
            count += 1
            if count >= 5: break

if __name__ == "__main__":
    find_active_markets()
