
import asyncio
import httpx
from app.core.client import PolyClient
from app.core.config import settings

async def test_clob_access():
    tid = "10681012694514548056594876622281200838879219112957871935242"
    poly = PolyClient.get_instance()
    
    print(f"Testing TID: {tid}")
    
    # 1. SDK
    try:
        book = poly.sdk.get_order_book(tid)
        print(f"SDK Bids: {len(book.bids)}")
    except Exception as e:
        print(f"SDK Error: {e}")
        
    # 2. Raw HTTP
    async with httpx.AsyncClient() as client:
        url = f"https://clob.polymarket.com/book?token_id={tid}"
        try:
            resp = await client.get(url)
            print(f"HTTP Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"HTTP Bids: {len(data.get('bids', []))}")
            else:
                print(f"HTTP Body: {resp.text[:200]}")
        except Exception as e:
            print(f"HTTP Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_clob_access())
