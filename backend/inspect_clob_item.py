
import httpx
import json

def inspect_clob_item():
    base = "https://clob.polymarket.com"
    r = httpx.get(f"{base}/markets")
    data = r.json()
    items = data.get('data', [])
    if items:
        item = items[0]
        print(f"Market: {item.get('question')}")
        tokens = item.get('tokens', [])
        print(f"Tokens: {tokens}")
        if tokens:
            tid = tokens[0].get('token_id')
            # Check price
            pr = httpx.get(f"{base}/price?token_id={tid}")
            print(f"  Price Status: {pr.status_code}")
            if pr.status_code == 200:
                print(f"  Price Data: {pr.json()}")
            
            # Check book
            ob = httpx.get(f"{base}/book?token_id={tid}")
            print(f"  Book Status: {ob.status_code}")

if __name__ == "__main__":
    inspect_clob_item()
