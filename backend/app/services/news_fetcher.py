import os
import httpx
import logging
from typing import List, Dict

logger = logging.getLogger("NewsFetcher")

class CryptoPanicFetcher:
    def __init__(self):
        self.api_key = os.getenv("CRYPTOPANIC_API_KEY")
        self.base_url = "https://cryptopanic.com/api/v1/posts/"

    async def fetch_latest_news(self, filter_type: str = "hot") -> List[Dict]:
        """
        Fetches latest news from CryptoPanic.
        """
        if not self.api_key or "your_" in self.api_key:
            logger.warning("No CryptoPanic API key found. Returning mock news.")
            return self._get_mock_news()

        try:
            params = {
                "auth_token": self.api_key,
                "public": "true",
                "filter": filter_type
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                news_items = []
                for item in results[:5]: # Take top 5
                    news_items.append({
                        "title": item.get("title"),
                        "source": item.get("domain"),
                        "url": item.get("url"),
                        "published_at": item.get("published_at")
                    })
                return news_items
        except Exception as e:
            logger.error(f"Error fetching news from CryptoPanic: {e}")
            return self._get_mock_news()

    def _get_mock_news(self) -> List[Dict]:
        return [
            {
                "title": "Fed Chair Powell: 'Inflation remains elevated, and we are prepared to raise rates further if necessary.'",
                "source": "MockFinance",
                "url": "#",
                "published_at": "Now"
            },
            {
                "title": "Bitcoin Whales Accumulate $2B in 24 Hours as Market Anticipates ETF Decision",
                "source": "ChainWatch",
                "url": "#",
                "published_at": "2h ago"
            }
        ]
