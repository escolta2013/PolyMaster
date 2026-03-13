from pydantic import BaseModel

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
        if stats.volume_usdc >= 1000000 and stats.roi >= 0.15:
            return "WHALE"
        
        # 2. SHARK: Skilled high-volume players
        if stats.volume_usdc >= 100000 and stats.roi >= 0.20 and stats.win_rate >= 0.60:
            return "SHARK"
            
        # 3. ORCA: Profitable regulars
        if stats.roi >= 0.15 and stats.win_rate >= 0.55 and stats.total_trades >= 30:
            return "ORCA"
            
        # 4. FISH: Profitable but low volume or few trades
        if stats.profit_usdc > 0 and stats.roi > 0:
            return "FISH"
            
        # 5. PLANKTON: Unprofitable or noise
        return "PLANKTON"

    def is_smart_money(self, grade: str) -> bool:
        return grade in ["WHALE", "SHARK", "ORCA"]
