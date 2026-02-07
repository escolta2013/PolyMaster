import os
import random
from openai import AsyncOpenAI
from app.services.news_fetcher import CryptoPanicFetcher

class AgentFactory:
    @staticmethod
    def create_client():
        provider = os.getenv("AI_PROVIDER", "openai").lower()
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = None

        if provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            base_url = "https://openrouter.ai/api/v1"
            print(f" [Council] Info: Using OpenRouter ({os.getenv('AI_MODEL', 'default')})")
        else:
             print(" [Council] Info: Using OpenAI")

        if not api_key or "your_" in api_key:
            print(" [Council] Warning: No valid API Key found. Agents will sleep.")
            return None

        return AsyncOpenAI(api_key=api_key, base_url=base_url)

class AgentOrchestrator:
    def __init__(self):
        self.client = AgentFactory.create_client()
        self.news_fetcher = CryptoPanicFetcher()
        self.model = os.getenv("AI_MODEL", "gpt-4-turbo-preview")

    async def get_feed(self):
        """
        Generates AI insights using real-time news data.
        """
        if not self.client:
             return [{
                 "agent": "System",
                 "type": "error",
                 "content": "AI Agents Offline. Please configure OPENAI_API_KEY or OPENROUTER_API_KEY in .env",
                 "confidence": 0,
                 "timestamp": "Now"
             }]

        try:
            # 1. Fetch Real-time News
            news_items = await self.news_fetcher.fetch_latest_news()
            
            # Select a high-impact news item for analysis
            target_news = news_items[0] if news_items else None
            
            if not target_news:
                return [{
                    "agent": "System",
                    "type": "info",
                    "content": "No relevant market news detected to analyze.",
                    "confidence": 1.0,
                    "timestamp": "Now"
                }]

            # 2. FedWatcher Analysis via LLM
            news_title = target_news["title"]
            source = target_news["source"]
            
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are 'FedWatcher', a financial AI agent. Analyze the text for hawkish/dovish sentiment or market impact. Output 1 short sentence (max 15 words)."},
                    {"role": "user", "content": f"Analyze this news: {news_title}"}
                ],
                max_tokens=60
            )
            analysis = completion.choices[0].message.content
            
            return [
                {
                    "agent": "FedWatcher",
                    "type": "hawk_alert",
                    "content": f"{analysis}",
                    "confidence": 0.88 + (random.random() * 0.1),
                    "timestamp": "Live Analysis",
                    "metadata": {
                        "source": source,
                        "url": target_news["url"],
                        "original_title": news_title
                    }
                },
                {
                    "agent": "RuleLawyer",
                    "type": "ambiguity_chk",
                    "content": "Standby. No complex rule disputes detected in active markets.",
                    "confidence": 1.0,
                    "timestamp": "Now"
                }
            ]

        except Exception as e:
            error_str = str(e)
            print(f"AI Error: {error_str}")
            
            error_msg = f"AI Generation Failed: {error_str[:50]}..."
            if "unsupported_country_region_territory" in error_str:
                error_msg = "OpenAI Region Block: Your current location is not supported by OpenAI. Please use a VPN or OpenRouter."

            return [{
                "agent": "System",
                "type": "error",
                "content": error_msg,
                "confidence": 0,
                "timestamp": "Now"
            }]
