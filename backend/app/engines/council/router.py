from fastapi import APIRouter, Body
from app.engines.council.orchestrator import AgentOrchestrator
from app.engines.ghost.scanner import MarketScanner

router = APIRouter(prefix="/council", tags=["Council Engine"])
orchestrator = AgentOrchestrator()
scanner = MarketScanner()

@router.get("/status")
def get_status():
    return {
        "status": "online",
        "active_agents": ["FedWatcher", "RuleLawyer", "SentimentSwarm", "MacroMind"],
        "governance": "Consensus (66%)"
    }

@router.get("/feed")
async def get_agent_feed():
    """
    Returns the real AI swarm analysis for the top trending markets.
    """
    # 1. Get top potential markets from Ghost scanner
    markets = scanner.scan_hype_spikes()
    
    if not markets:
        return []

    # 2. Run Council Consensus on the top 3 markets
    analysis_tasks = [orchestrator.get_market_consensus(m) for m in markets[:3]]
    consensuses = await asyncio.gather(*analysis_tasks)
    
    # 3. Format feed for UI
    feed = []
    for i, cons in enumerate(consensuses):
        feed.append({
            "id": markets[i]['id'],
            "market_name": markets[i]['question'],
            "intensity_score": markets[i]['spike_magnitude'],
            "consensus": "YES" if cons['consensus_reached'] else "DIVERGENT",
            "confidence": cons['aggregate_score'],
            "reasoning": cons['agent_reports'][0]['reasoning'] if cons['agent_reports'] else "Analyzing...",
            "agent_reports": cons['agent_reports'], # Include full breakdown
            "timestamp": cons['timestamp']
        })
        
    return feed

import asyncio # Needed for gather
