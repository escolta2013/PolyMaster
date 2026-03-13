import requests
import json
import asyncio
import httpx

async def find_test_market():
    # Fetch from trending/volume
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 50,
        "active": "true",
        "closed": "false"
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        markets = resp.json()
        
        for m in markets:
            q = m.get("question")
            tids = m.get("clobTokenIds")
            if not tids: continue
            if isinstance(tids, str): tids = json.loads(tids)
            if not tids: continue
            tid = tids[0]
            
            # Check CLOB price
            try:
                ob_url = f"https://clob.polymarket.com/book?token_id={tid}"
                ob_resp = await client.get(ob_url)
                if ob_resp.status_code == 200:
                    ob = ob_resp.json()
                    asks = ob.get("asks", [])
                    bids = ob.get("bids", [])
                    if asks and bids:
                        ask = float(asks[0]["price"])
                        bid = float(bids[0]["price"])
                        mid = (ask + bid) / 2
                        spread = ask - bid
                        if 0.35 <= mid <= 0.65 and spread < 0.25:
                            print(f"MATCH: {q}")
                            print(f"TID: {tid}")
                            print(f"Price: {mid:.3f} | Spread: {spread:.3f}")
                            # return tid
            except: pass

if __name__ == "__main__":
    asyncio.run(find_test_market())
