from fastapi import APIRouter
from app.engines.council.agents import AgentOrchestrator

router = APIRouter(prefix="/council", tags=["Council Engine"])
orchestrator = AgentOrchestrator()

@router.get("/status")
def get_status():
    return {
        "status": "online",
        "active_agents": ["FedWatcher", "RuleLawyer", "SentimentSwarm"]
    }

@router.get("/feed")
async def get_agent_feed():
    """
    Returns a stream of AI agent insights (Real AI).
    """
    return await orchestrator.get_feed()
