from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.engines.tracker.indexer import PolymarketIndexer
from app.engines.tracker.grader import WalletGrader, WalletStats
from app.engines.tracker.tracker import SmartMoneyTracker
from app.engines.tracker.cluster_detector import ClusterDetector
from app.engines.tracker.copy_executor import CopyExecutor, CopyTradeRequest

router = APIRouter(prefix="/tracker", tags=["Tracker"])
tracker = SmartMoneyTracker()
cluster_detector = ClusterDetector(min_wallets=3)
copy_executor = CopyExecutor()


# ---------------------------------------------------------------------------
# Existing endpoints
# ---------------------------------------------------------------------------

@router.get("/top-markets")
async def get_top_markets(limit: int = 10):
    markets = tracker.indexer.get_top_markets(limit)
    return {"count": len(markets), "markets": markets}


@router.get("/wallets")
async def get_wallets(grade: str = None, sort_by: str = "roi", limit: int = 50):
    """
    Fetch wallets with optional filtering and sorting.
    """
    try:
        query = tracker.supabase.table("wallets").select("*")
        if grade:
            query = query.eq("grade", grade.upper())
        
        # Determine sorting column
        sort_col = "roi"
        if sort_by == "volume": sort_col = "volume_usdc"
        if sort_by == "profit": sort_col = "profit_usdc"
        
        response = query.order(sort_col, desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """
    Fetch high-level tracking statistics including cluster alert count.
    """
    try:
        res = tracker.supabase.table("wallets").select("grade, is_smart_money, volume_usdc, profit_usdc").execute()
        data = res.data
        
        # Count recent cluster alerts
        cluster_count = 0
        try:
            alerts_res = tracker.supabase.table("cluster_alerts").select("alert_id", count="exact").execute()
            cluster_count = len(alerts_res.data) if alerts_res.data else 0
        except Exception:
            pass

        stats = {
            "total_tracked": len(data),
            "smart_money_count": len([d for d in data if d["is_smart_money"]]),
            "total_volume": sum(d.get("volume_usdc", 0) or 0 for d in data),
            "total_profit": sum(d.get("profit_usdc", 0) or 0 for d in data),
            "cluster_alerts": cluster_count,
            "by_grade": {
                "WHALE": len([d for d in data if d["grade"] == "WHALE"]),
                "SHARK": len([d for d in data if d["grade"] == "SHARK"]),
                "ORCA": len([d for d in data if d["grade"] == "ORCA"]),
                "FISH": len([d for d in data if d["grade"] == "FISH"]),
                "PLANKTON": len([d for d in data if d["grade"] == "PLANKTON"]),
            }
        }
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def trigger_sync():
    """
    Manually trigger a market scan and wallet grading cycle.
    """
    try:
        await tracker.update_smart_money_list()
        return {"status": "Sync completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Cluster Detection endpoints
# ---------------------------------------------------------------------------

@router.post("/clusters/scan")
async def scan_clusters():
    """
    Manually trigger a cluster detection scan.
    Checks if ≥3 smart-money wallets converge on the same market outcome.
    """
    try:
        alerts = await cluster_detector.scan_for_clusters()
        return {
            "status": "scan_complete",
            "new_alerts": len(alerts),
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "market_question": a.market_question,
                    "outcome": a.outcome,
                    "wallet_count": a.wallet_count,
                    "wallet_grades": a.wallet_grades,
                    "total_exposure": a.total_exposure,
                    "confidence": a.confidence,
                    "detected_at": a.detected_at,
                }
                for a in alerts
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters/alerts")
async def get_cluster_alerts(limit: int = 20):
    """
    Fetch recent cluster alerts from the database.
    """
    try:
        alerts = cluster_detector.get_recent_alerts(limit=limit)
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Copy Trading endpoints
# ---------------------------------------------------------------------------

class CopyTradeBody(BaseModel):
    source_wallet: str
    token_id: str
    market_id: str
    market_question: str = ""
    outcome: str = "YES"
    price: float
    size_usdc: float = 50.0


@router.post("/copy")
async def execute_copy_trade(body: CopyTradeBody):
    """
    Execute a copy trade — replicate a smart-money wallet's position.
    Respects per-trade and daily exposure limits.
    """
    try:
        req = CopyTradeRequest(
            source_wallet=body.source_wallet,
            token_id=body.token_id,
            market_id=body.market_id,
            market_question=body.market_question,
            outcome=body.outcome,
            price=body.price,
            size_usdc=body.size_usdc,
        )
        result = copy_executor.execute_copy(req)
        return {
            "status": result.status,
            "order_id": result.order_id,
            "message": result.message,
            "trade": result.trade,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/copy/status")
async def get_copy_status():
    """
    Get current copy-executor status: simulation mode, limits, daily usage.
    """
    return copy_executor.get_status()


@router.get("/copy/log")
async def get_copy_log(limit: int = 20):
    """
    Fetch the copy-trade history log.
    """
    return copy_executor.get_trade_log(limit=limit)
