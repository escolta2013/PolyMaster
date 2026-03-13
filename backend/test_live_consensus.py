import asyncio
import os
import sys

# Ensure backend directory is in path and dotenv is loaded
sys.path.append(os.path.join(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from app.engines.autonomous.director import DirectorAgent
from app.core.logging import logger

async def run_manual_test():
    logger.info("Starting Manual Test of Director / Council.")
    director = DirectorAgent()
    
    # 1. Monkeypatch the orderbook to force the conditions the user wants:
    # "precio CLOB entre 0.35 y 0.65, spread menor a 0.25"
    # We will set a best_bid of 0.40 and best_ask of 0.55 -> Price (midpoint) = 0.475, Spread = 0.15
    original_get_orderbook = director.executor.client.get_orderbook
    
    async def mock_get_orderbook(token_id: str) -> dict:
        return {
            "bids": [{"price": "0.40", "size": "1000"}],
            "asks": [{"price": "0.55", "size": "1000"}],
            "best_bid": 0.40,
            "best_ask": 0.55,
            "spread": 0.15,
            "midpoint": 0.475
        }
    director.executor.client.get_orderbook = mock_get_orderbook

    # 2. Prepare the manually crafted alert
    # We use a real-world, active question so the AI Council can actually research it and score it.
    mock_alert = {
        "market_id": "mock_market_777",
        "market_question": "Will Donald Trump deport less than 250,000 people in his first 100 days?",
        "token_id": "75780541925079646493083961813747713993684746109825075536555618593417966065654",
        "outcome": "YES",
        "confidence": 0.85, # Simulated high-conviction whale cluster
        "end_date": "2026-05-01T00:00:00Z",
        "whale_count": 3,
        "source": "WHALE_TRACKER_TEST"
    }

    # 3. Clear cache for this specific market so it forces a re-evaluation
    from app.engines.council.cache import council_cache
    council_cache._cache.pop("mock_market_777", None)

    # 4. Execute the Director
    logger.info("Executing Director with mocked Orderbook (Price: 0.475, Spread: 0.15)...")
    result = await director.evaluate_and_execute(mock_alert)
    
    logger.success(f"Final Result: {result}")

if __name__ == "__main__":
    asyncio.run(run_manual_test())
