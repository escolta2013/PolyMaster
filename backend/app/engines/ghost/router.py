from fastapi import APIRouter, HTTPException, Body
from app.engines.ghost.scanner import MarketScanner
from app.engines.ghost.liquidity import LiquidityManager

router = APIRouter(prefix="/ghost", tags=["Ghost Engine"])
scanner = MarketScanner()
liquidity = LiquidityManager()

@router.get("/status")
def get_status():
    return {
        "status": "online",
        "mode": "statistical_arbitrage",
        "active_scanners": ["hype_spike", "liquidity_gap"],
        "simulation_mode": liquidity.simulation_mode
    }

@router.get("/scan")
def scan_markets():
    """
    Returns a list of high-volatility markets (mocked for now).
    """
    return scanner.scan_hype_spikes()

@router.post("/execution-mode")
def set_execution_mode(simulation: bool = Body(..., embed=True)):
    liquidity.set_execution_mode(simulation)
    return {"status": "success", "simulation_mode": simulation}

@router.post("/strategy/start")
def start_strategy(market_id: str = Body(...), token_id: str = Body(...)):
    return liquidity.place_spread_orders(market_id, token_id)

@router.post("/strategy/stop")
def stop_strategy():
    return liquidity.cancel_all()
