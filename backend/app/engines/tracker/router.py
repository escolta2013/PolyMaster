from fastapi import APIRouter, HTTPException
from app.engines.tracker.indexer import PolymarketIndexer
from app.engines.tracker.grader import WalletGrader, WalletStats

from app.engines.tracker.tracker import SmartMoneyTracker

router = APIRouter(prefix="/tracker", tags=["Tracker"])
tracker = SmartMoneyTracker()

@router.get("/top-markets")
async def get_top_markets(limit: int = 10):
    markets = tracker.indexer.get_top_markets(limit)
    return {"count": len(markets), "markets": markets}

@router.get("/smart-money")
async def get_smart_money():
    """
    Fetch the list of identified smart money wallets from the database.
    """
    try:
        response = tracker.supabase.table("wallets").select("*").eq("is_smart_money", True).execute()
        return response.data
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
