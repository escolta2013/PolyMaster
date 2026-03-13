
import asyncio
import httpx
from loguru import logger

async def test_gamma():
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 10,
        "order": "volume",
        "ascending": "false",
        "active": "true"
    }
    async with httpx.AsyncClient() as client:
        try:
            logger.info("Testing Gamma API...")
            resp = await client.get(url, params=params, timeout=10)
            logger.info(f"Gamma Status: {resp.status_code}")
            if resp.status_code == 200:
                logger.success("Gamma API OK")
        except Exception as e:
            logger.error(f"Gamma API Error: {e}")

async def test_data(address):
    url = f"https://data-api.polymarket.com/positions"
    params = {"user": address}
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Testing Data API for {address}...")
            resp = await client.get(url, params=params, timeout=10)
            logger.info(f"Data API Status for {address}: {resp.status_code}")
            if resp.status_code == 200:
                logger.success(f"Data API OK for {address}")
        except Exception as e:
            logger.error(f"Data API Error for {address}: {e}")

async def main():
    await test_gamma()
    # Using a valid hex address to avoid 400 Bad Request
    await test_data("0x8d4659690184DFe8f73Ba350B42A633D5f0610") 
    await test_data("0x70997970C51812dc3A010C7d01b50e0d17dc79C8")

if __name__ == "__main__":
    asyncio.run(main())
