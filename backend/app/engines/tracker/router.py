from fastapi import APIRouter, HTTPException
from app.engines.tracker.indexer import PolymarketIndexer
from app.engines.tracker.grader import WalletGrader, WalletStats

router = APIRouter(prefix="/tracker", tags=["Tracker"])
indexer = PolymarketIndexer()
grader = WalletGrader()

@router.get("/top-markets")
async def get_top_markets(limit: int = 10):
    """
    Get top markets to scan for whale activity.
    """
    markets = indexer.get_top_markets(limit)
    return {"count": len(markets), "markets": markets}

@router.post("/grade-wallet")
async def grade_wallet(stats: WalletStats):
    """
    Grade a wallet based on its stats.
    """
    grade = grader.grade_wallet(stats)
    return {
        "address": stats.address,
        "grade": grade,
        "is_smart_money": grader.is_smart_money(grade)
    }
