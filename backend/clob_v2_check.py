
import httpx
import json

def check_clob_v2():
    base = "https://clob.polymarket.com"
    # Get markets
    r = httpx.get(f"{base}/markets", params={"limit": 5})
    if r.status_code == 200:
        data = r.json().get('data', [])
        for item in data:
            print(f"Question: {item.get('question')}")
            tokens = item.get('tokens', [])
            for t in tokens:
                tid = t.get('token_id')
                print(f"  Token: {t.get('outcome')} | ID: {tid}")
                # Try book
                br = httpx.get(f"{base}/book?token_id={tid}")
                print(f"    Book Status: {br.status_code}")
                if br.status_code == 200:
                    print(f"    Bids: {len(br.json().get('bids', []))}")
                else:
                    print(f"    Error: {br.text[:100]}")
            print("-" * 20)

if __name__ == "__main__":
    check_clob_v2()
