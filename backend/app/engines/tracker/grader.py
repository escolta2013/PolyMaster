from pydantic import BaseModel

class WalletStats(BaseModel):
    address: str
    roi: float  # Percentage (e.g., 0.25 for 25%)
    win_rate: float # Percentage (e.g., 0.60)
    total_trades: int
    profit_usdc: float

class WalletGrader:
    """
    Grades wallets based on performance metrics to filter 'Smart Money'.
    Strategy Reference: Reddit 'Wallet Grading' (A-D)
    """
    
    def grade_wallet(self, stats: WalletStats) -> str:
        # Tier A: The Whales / Sharps
        # High volume, high conviction, consistent returns
        if stats.roi >= 0.20 and stats.win_rate >= 0.60 and stats.total_trades > 50:
            return "A"
            
        # Tier B: Profitable Regulars
        # Good signals but maybe less volume or slightly more risk
        if stats.roi >= 0.10 and stats.win_rate > 0.50 and stats.total_trades > 20:
            return "B"
            
        # Tier C: Break-even / Noise
        if stats.roi >= 0.0:
            return "C"
            
        # Tier D: Rekt / Gamblers
        return "D"

    def is_smart_money(self, grade: str) -> bool:
        return grade in ["A", "B"]
