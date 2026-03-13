import requests
import json
import asyncio
import httpx

async def find_market():
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 50,
        "active": "true",
        "closed": "false",
        "order": "volume",
        "ascending": "false"
    }
    r = requests.get(url, params=params)
    markets = r.json()
    
    tasks = []
    # Keep track of which market corresponds to which task
    market_list = []
    
    async with httpx.AsyncClient() as client:
        for m in markets:
            tids = m.get("clobTokenIds")
            if tids:
                try: tids = json.loads(tids)
                except: continue
                if not tids: continue
                tid = tids[0] if isinstance(tids, list) else tids
                book_url = f"https://clob.polymarket.com/book?token_id={tid}"
                tasks.append(client.get(book_url))
                market_list.append(m)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, res in enumerate(results):
            if isinstance(res, httpx.Response) and res.status_code == 200:
                ob = res.json()
                asks = ob.get("asks", [])
                bids = ob.get("bids", [])
                if asks and bids:
                    ask = float(asks[0]["price"])
                    bid = float(bids[0]["price"])
                    mid = (ask+bid)/2
                    spr = ask-bid
                    if 0.30 <= mid <= 0.70 and spr < 0.15:
                         print(f"MATCH! TID: {market_list[i].get('clobTokenIds')} | P: {mid:.3f} | S: {spr:.3f}")
                         print(f"Q: {market_list[i].get('question')}")
                         return

if __name__ == "__main__":
    asyncio.run(find_market())
