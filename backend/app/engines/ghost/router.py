from fastapi import APIRouter, HTTPException
from app.engines.ghost.scanner import MarketScanner

router = APIRouter(prefix="/ghost", tags=["Ghost Engine"])
scanner = MarketScanner()

@router.get("/status")
def get_status():
    return {
        "status": "online",
        "mode": "statistical_arbitrage",
        "active_scanners": ["hype_spike", "liquidity_gap"]
    }

@router.get("/scan")
def scan_markets():
    """
    Returns a list of high-volatility markets (mocked for now).
    """
    return scanner.scan_hype_spikes()
