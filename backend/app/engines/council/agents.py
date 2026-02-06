import os
import random
from openai import AsyncOpenAI

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
        self.model = os.getenv("AI_MODEL", "gpt-4-turbo-preview")

    async def get_feed(self):
        """
        Generates AI insights.
        In a real scenario, this would trigger background tasks.
        For now, we generate ON-DEMAND insights for the frontend.
        """
        if not self.client:
             return [{
                 "agent": "System",
                 "type": "error",
                 "content": "AI Agents Offline. Please configure OPENAI_API_KEY or OPENROUTER_API_KEY in .env",
                 "confidence": 0,
                 "timestamp": "Now"
             }]

        # 1. FedWatcher Logic (Mock Trigger, Real Generation)
        # In prod: fetch news -> sending to LLM.
        # Here: We simulate a "News Event" and ask LLM to analyze it.
        try:
            # We skip real LLM call for every refresh to save money/latency in dev.
            # We'll make a real call only 20% of the time or if requested.
            # adjusting to ALWAYS call for demo purposes if user wants?
            # Let's keep it safe: Mock the news, but use LLM to ANALYZE the mock news.
            
            news_snippet = "Fed Chair Powell: 'Inflation remains elevated, and we are prepared to raise rates further if necessary.'"
            
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are 'FedWatcher', a financial AI agent. Analyze the text for hawkish/dovish sentiment. Output 1 short sentence."},
                    {"role": "user", "content": f"Analyze this news: {news_snippet}"}
                ],
                max_tokens=60
            )
            analysis = completion.choices[0].message.content
            
            return [
                {
                    "agent": "FedWatcher",
                    "type": "hawk_alert",
                    "content": f"{analysis}",
                    "confidence": 0.92,
                    "timestamp": "Live Analysis"
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
            print(f"AI Error: {e}")
            return [{
                "agent": "System",
                "type": "error",
                "content": f"AI Generation Failed: {str(e)[:50]}...",
                "confidence": 0,
                "timestamp": "Now"
            }]
