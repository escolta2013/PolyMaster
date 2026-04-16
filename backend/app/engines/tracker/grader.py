from pydantic import BaseModel
from app.core.config import settings

class WalletStats(BaseModel):
    address: str
    roi: float  # Percentage (e.g., 0.25 for 25%)
    win_rate: float # Percentage (e.g., 0.60)
    total_trades: int
    profit_usdc: float
    volume_usdc: float

class WalletGrader:
    """
    Grades wallets based on performance metrics to filter 'Smart Money'.
    Strategy Reference: Reddit 'Wallet Grading' (A-D)
    """
    
    def grade_wallet(self, stats: WalletStats) -> str:
        """
        Grades wallets based on volume, ROI, and win rate.
        Tiers: WHALE, SHARK, ORCA, FISH, PLANKTON
        """
        # 1. WHALE: High volume giants
        if stats.volume_usdc >= settings.GRADE_WHALE_VOL and stats.roi >= settings.GRADE_WHALE_ROI:
            return "WHALE"
        
        # 2. SHARK: Skilled high-volume players
        if stats.volume_usdc >= settings.GRADE_SHARK_VOL and stats.roi >= settings.GRADE_SHARK_ROI and stats.win_rate >= settings.GRADE_SHARK_WINRATE:
            return "SHARK"
            
        # 3. ORCA: Profitable regulars
        if stats.roi >= settings.GRADE_ORCA_ROI and stats.win_rate >= settings.GRADE_ORCA_WINRATE and stats.total_trades >= settings.GRADE_ORCA_TRADES:
            return "ORCA"
            
        # 4. FISH: Profitable but low volume or few trades
        if stats.profit_usdc > 0 and stats.roi > 0:
            return "FISH"
            
        # 5. PLANKTON: Unprofitable or noise
        return "PLANKTON"

    def is_smart_money(self, grade: str) -> bool:
        return grade in ["WHALE", "SHARK", "ORCA"]
