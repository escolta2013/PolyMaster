import asyncio
from app.services.news_fetcher import CryptoPanicFetcher

async def test_news_fetcher():
    fetcher = CryptoPanicFetcher()
    print("Testing NewsFetcher...")
    
    # Test fetch (will either get real news or fallback to mock)
    news = await fetcher.fetch_latest_news()
    
    if news:
        print(f"SUCCESS: Fetched {len(news)} news items.")
        for i, item in enumerate(news[:2]):
            print(f"ITEM {i}: {item['title']} (Source: {item['source']})")
    else:
        print("FAILURE: No news items returned.")

if __name__ == "__main__":
    asyncio.run(test_news_fetcher())
