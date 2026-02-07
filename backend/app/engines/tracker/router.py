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
    Fetch high-level tracking statistics.
    """
    try:
        res = tracker.supabase.table("wallets").select("grade, is_smart_money, volume_usdc, profit_usdc").execute()
        data = res.data
        
        stats = {
            "total_tracked": len(data),
            "smart_money_count": len([d for d in data if d["is_smart_money"]]),
            "total_volume": sum(d.get("volume_usdc", 0) or 0 for d in data),
            "total_profit": sum(d.get("profit_usdc", 0) or 0 for d in data),
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
