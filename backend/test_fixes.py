
import asyncio
import os
from loguru import logger
from app.engines.tracker.cluster_detector import ClusterDetector
from app.engines.tracker.copy_executor import CopyExecutor
from app.engines.council.orchestrator import AgentOrchestrator

# Mock settings just in case, but they should load from env
os.environ["ENABLE_AUTONOMOUS_TRADING"] = "true"

async def test_cluster_detector_init():
    logger.info("Testing ClusterDetector initialization...")
    detector = ClusterDetector()
    await detector._ensure_initialized()
    logger.info(f"Recent alerts cache size: {len(detector._recent_alerts)}")

async def test_copy_executor_sync():
    logger.info("Testing CopyExecutor sync...")
    executor = CopyExecutor()
    status = executor.get_status()
    logger.info(f"CopyExecutor status: {status}")

async def test_orchestrator_na_price():
    logger.info("Testing AgentOrchestrator with N/A price...")
    orchestrator = AgentOrchestrator()
    # Mock data with N/A price
    market_data = {
        "id": "test_market",
        "question": "Will this test pass?",
        "price": "N/A",
        "spike_magnitude": 0.5
    }
    # We don't want to actually call OpenAI, just test the float conversion logic in get_market_consensus
    # But get_market_consensus calls agent.analyze which calls OpenAI.
    # We can mock the agents or just rely on SimulationAgent if no key.
    # Actually, we can just check the specific method if we could import it, but it's inside get_market_consensus.
    
    # Strategy: We can wrap the call in try/except.
    # But we don't want to burn API credits.
    # Check if we have API key. If yes, this test will cost money/tokens.
    # Maybe we can mock the agents list?
    orchestrator.agents = [] # Remove agents to skip analysis
    
    # But get_market_consensus iterates agents.
    # Let's add a dummy agent
    from app.engines.council.orchestrator import SimulationAgent
    orchestrator.agents = [SimulationAgent("TestBot", "Passive")]
    
    try:
        result = await orchestrator.get_market_consensus(market_data)
        logger.success(f"Orchestrator handled N/A price: Final Score {result.get('final_score')}")
    except Exception as e:
        logger.error(f"Orchestrator failed on N/A price: {e}")

async def main():
    await test_cluster_detector_init()
    await test_copy_executor_sync()
    await test_orchestrator_na_price()

if __name__ == "__main__":
    asyncio.run(main())
