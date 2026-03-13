from fastapi import APIRouter, HTTPException, Body
from app.engines.ghost.scanner import MarketScanner
from app.engines.ghost.liquidity import LiquidityManager
from app.engines.ghost.merger import PositionMerger

router = APIRouter(prefix="/ghost", tags=["Ghost Engine"])
scanner = MarketScanner()
liquidity = LiquidityManager()
merger = PositionMerger()

@router.get("/status")
def get_status():
    return {
        "status": "online",
        "mode": "statistical_arbitrage",
        "active_scanners": ["hype_spike", "liquidity_gap", "NEH_decay"],
        "simulation_mode": liquidity.simulation_mode,
        "risk_limits": liquidity.risk_manager.risk_params,
        "active_markets": list(liquidity.active_orders.keys()),
        "current_spread": liquidity.target_spread
    }

@router.get("/scan")
def scan_markets():
    return scanner.scan_hype_spikes()

@router.post("/execution-mode")
def set_execution_mode(simulation: bool = Body(..., embed=True)):
    liquidity.set_execution_mode(simulation)
    merger.simulation_mode = simulation
    return {"status": "success", "simulation_mode": simulation}

@router.post("/strategy/start")
def start_strategy(
    market_id: str = Body(...), 
    token_id: str = Body(...),
    strategy: str = Body("liquidity_grinder"),
    size: float = Body(None)
):
    # Use the size from risk manager if not provided
    exec_size = size or liquidity.risk_manager.risk_params.get("position_cap_amount", 10.0)
    
    if strategy == "neh":
        return liquidity.place_neh_order(market_id, token_id, size=exec_size)
    return liquidity.place_spread_orders(market_id, token_id, spread_width=liquidity.target_spread, size=exec_size)

@router.post("/strategy/stop")
def stop_strategy():
    return liquidity.cancel_all()

@router.post("/merge/scan")
async def scan_merges(user_address: str = Body(..., embed=True)):
    return await merger.scan_and_merge(user_address)

@router.post("/risk/configure")
def update_risk(params: dict = Body(...)):
    # Special handling for spread which lives in liquidity manager
    if "spread_width" in params:
        liquidity.target_spread = float(params["spread_width"])
    
    # Other params go to risk manager
    risk_data = {k: v for k, v in params.items() if k != "spread_width"}
    if risk_data:
        liquidity.risk_manager.set_risk_params(risk_data)
        
    return {
        "status": "success", 
        "risk_params": liquidity.risk_manager.risk_params,
        "spread": liquidity.target_spread
    }
