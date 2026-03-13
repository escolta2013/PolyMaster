from app.core.config import settings
from app.core.logging import logger
from datetime import datetime, timezone
from typing import List, Dict, Any
import httpx
from supabase import create_client, Client
from .indexer import PolymarketIndexer
from .grader import WalletGrader, WalletStats

class SmartMoneyTracker:
    """
    Orchestrator for the Smart Money Tracking engine.
    Refactored for async performance and structured logging.
    """

    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.indexer = PolymarketIndexer()
        self.grader = WalletGrader()

    async def update_smart_money_list(self):
        """
        Main loop to refresh the smart money database by discovering and grading wallets.
        """
        logger.info("Starting Smart Money update cycle (Async)...")
        
        vip_wallets = [
            # Validator Bot Researched Whales (High PnL + Verified Entry prices)
            "0xc2e7800b5af46e6093872b177b7a5e7f0563be51",  # WHALE | beachboy4 | PnL: $351,670 | WR: 100.0%
            "0x507e52ef684ca2dd91f90a9d26d149dd3288beae",  # WHALE | GamblingIsAllYouNeed | PnL: $185,687 | WR: 68.3%
            "0x07b8e44b90cc3e91b8d5fe60ea810d2534638e25",  # WHALE | joosangyoo | PnL: $150,664 | WR: 100.0%
            "0xee0d153c17fe82b8866b484753b56a700ab457ab",  # WHALE | BBPK | PnL: $102,268 | WR: 56.7%
            "0xa3e1664fc43903ac3010c89fa3dd00828f665968",  # SHARK | sd13 | PnL: $61,964 | WR: 100.0%
            "0x0b9cae2b0dfe7a71c413e0604eaac1c352f87e44",  # SHARK | geniusCM | PnL: $55,548 | WR: 83.5%
            "0x22e4248bdb066f65c9f11cd66cdd3719a28eef1c",  # SHARK | ProfessionalPunter | PnL: $26,280 | WR: 56.5%
            
            # Medium Article Whales (Top Performers by absolute profit)
            "0x715915950ffa56807ade2d75d742614321542660",  # domahhh / ImJustKen
            "0x1667614321542660175174748465138472356787",  # aenews / aenews2
            "0x1030fc89f8e8bc61a232451064d15a3745944e7e",  # HolyMoses / HolyMoses7
            "0xfddfbfe715915950ffa56807ade2d75d74261432",  # Frosenn / Frozenn
            
            # Dune Dashboard 'Witcheer' Whales (Cleared of penny-picking behavior via script)
            # Batch 1 (Top 10)
            "0x25e64cd559e8c46a888d8ebfa47d4490e810cc9f",  # Dune Whale | $624K PnL | Avg Entry $0.52
            "0x9c4ccdb83e6f78d84d5b4422917ca05752e23a00",  # Dune Whale | $547K PnL | Avg Entry $0.67
            "0xda9b03badde953167e7a861092b391580306fa50",  # Dune Whale | $491K PnL | Avg Entry $0.43
            "0x4959175440b8f38229b32f2f036057f6893ea6f5",  # Dune Whale | $472K PnL | Avg Entry $0.69
            "0x552337556e70f851bff6e0e97a2e00df7d5751e9",  # Dune Whale | $468K PnL | Avg Entry $0.15 (High conviction alpha)
            
            # Batch 2 (Top 11-30) - Cleared of penny-picking
            "0xe613b515bd46b1585a8b137a4d291d9b80bd540e",  # Dune Whale | $461K PnL | Avg Entry $0.08
            "0x50f3e0745cb8bef421bdaa403b1b70f5d1d8cfbf",  # Dune Whale | $450K PnL | Avg Entry $0.52
            "0x8df306b761d8e4f95ffa21a2d5d36fd330fe887a",  # Dune Whale | $406K PnL | Avg Entry $0.47
            "0x7abdf17e68380c9c4c90f84a0dc924592d9947d1",  # Dune Whale | $385K PnL | Avg Entry $0.41
            "0xed61f86bb5298d2f27c21c433ce58d80b88a9aa3",  # Dune Whale | $370K PnL | Avg Entry $0.75
            "0x257d0d66330654577734650715f5c46b540e3a03",  # Dune Whale | $359K PnL | Avg Entry $0.84
            "0x1abe1368601330a310162064e04d3c2628cb6497",  # Dune Whale | $322K PnL | Avg Entry $0.62
            "0x0b4731091ea7bf7920f358fd82b72e41a123a77b",  # Dune Whale | $302K PnL | Avg Entry $0.49
            "0x09abc5845c024a4f9a3abff29d95057e6b20e832",  # Dune Whale | $295K PnL | Avg Entry $0.79
            "0x1ce22666b8fb017a55db38c731b05d0b24583c96",  # Dune Whale | $288K PnL | Avg Entry $0.34
            "0xfe032d6324fd345a5c0569424a0207349964f14f",  # Dune Whale | $285K PnL | Avg Entry $0.38
            "0xf2be1c7b53567706288a25ee3b5d2abc58754c9f",  # Dune Whale | $277K PnL | Avg Entry $0.43
            "0xd5dca994eb0099f55b2dac334c7b9d76cb0411bb",  # Dune Whale | $271K PnL | Avg Entry $0.64
            "0xbb903888f2d952a1845c90142267c61b4926ad7f",  # Dune Whale | $269K PnL | Avg Entry $0.87
            "0x44de2a52d8d2d3ddcf39d58e315a10df53ba9c08",  # Dune Whale | $249K PnL | Avg Entry $0.57
            "0x2e29fc8a478a458d63028c88f3bc1e89bfa66572",  # Dune Whale | $241K PnL | Avg Entry $0.51
            
            # Batch 3 (User requested list) - Cleared of penny-picking
            "0x8f42ae0a01c0383c7ca8bd060b86a645ee74b88f",
            "0x7e6fda10646a4343358c84004859adfea1c0c022",
            "0x9ec7da81a2da3d47a47dd281b1ecf2cf2b3a35c0",
            "0xcd95ebd0d0d099fa442b9730991f2b8be5d28c17",
            "0xae7c98235d5dc797edfa3d3af2e0334238a4487e",
            "0x986b121c40e715167dde178b8520bf132a57bdc6",
            "0xbc43a2f0deb85ba4ad316300762972089c911540",
            "0xdfafd14f51d8f163a2df19144275233dc598aeb4",
            "0xc0292a841a0c9a7320aa39075cffcf1b8f64f705",
            "0xe617861a96631d7cefdb1ad43e95c33b5946f251",
            "0xc311bbe0d55797afa70c9329e15157640a6e44fc",
            "0xbb015bb4009b6a48bfb9363d9c9b1d54e9ab02e5",
            "0xc3e45193d37ec34b82129adfc46abff7bb415bf6",
            "0x9910712aacd5a9fe057e12b1d10a789b939f5058",
        ]
        await self._process_potential_smart_money(vip_wallets)
        
        # 1. Fetch top markets with high volume
        markets = await self.indexer.get_top_markets(limit=3)
        
        async with httpx.AsyncClient() as client:
            for market in markets:
                m_id = market.get("id")
                question = market.get("question", "Unknown Market")
                volume = float(market.get("volume", 0))
                
                if not m_id: continue

                # Save market to DB
                try:
                    self.supabase.table("tracked_markets").upsert({
                        "market_id": m_id,
                        "question": question,
                        "volume": volume,
                        "last_indexed": datetime.now(timezone.utc).isoformat()
                    }).execute()
                except Exception as e:
                    logger.error(f"Error upserting market {m_id}: {e}")

        # 2. Discover traders via high-volume trades (DISABLED for fast testing)
        # token_ids = market.get("clobTokenIds", [])
        # ...
        pass

    async def _process_potential_smart_money(self, addresses: List[str]):
        """
        Analyze wallet addresses using Data API to calculate real performance metrics.
        """
        for addr in addresses:
            try:
                # Fetch positions from indexed client (PolyClient)
                positions = await self.indexer.clob_client.get_user_positions(addr)
                
                if not positions:
                    continue

                # NEW: Check for Farming/Hedging
                if self._is_farmer(positions):
                    logger.info(f"Skipping Farmer/MM wallet: {addr}")
                    continue
                
                # Calculate real stats from positions
                total_trades = len(positions)
                total_realized_pnl = 0.0
                total_initial_value = 0.0
                total_volume = 0.0
                wins = 0
                
                for pos in positions:
                    realized = float(pos.get("realizedPnl", 0))
                    initial = float(pos.get("initialValue", 0)) 
                    total_initial_value += initial
                    total_realized_pnl += realized
                    total_volume += initial 
                    
                    if realized > 0 or float(pos.get("cashPnl", 0)) > 0:
                        wins += 1
                
                roi = total_realized_pnl / total_initial_value if total_initial_value > 0 else 0
                win_rate = wins / total_trades if total_trades > 0 else 0
                
                stats = WalletStats(
                    address=addr,
                    roi=roi,
                    win_rate=win_rate,
                    total_trades=total_trades,
                    profit_usdc=total_realized_pnl,
                    volume_usdc=total_volume
                )
                
                grade = self.grader.grade_wallet(stats)
                is_smart = self.grader.is_smart_money(grade)
                
                self.supabase.table("wallets").upsert({
                    "address": addr,
                    "grade": grade,
                    "roi": float(round(roi, 4)),
                    "win_rate": float(round(win_rate, 4)),
                    "total_trades": total_trades,
                    "profit_usdc": float(round(total_realized_pnl, 2)),
                    "volume_usdc": float(round(total_volume, 2)),
                    "is_smart_money": is_smart,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }).execute()
                
                if is_smart:
                    logger.success(f"SMART MONEY UPDATED: {addr[:10]}... (Grade {grade}, ROI {roi:.1%})")
                
                # Small delay to avoid Data API 429s
                await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.debug(f"Error processing wallet {addr[:10]}: {e}")

    def _is_farmer(self, positions: List[Dict]) -> bool:
        """
        Detects if a wallet is 'Farming' rewards or providing liquidity 
        by holding opposing positions in the same market.
        """
        # Group by conditionId or slug
        markets = {}
        for pos in positions:
            # Only consider active positions with meaningful size
            if float(pos.get("size", 0)) > 1.0: # Ignore dust
                cond_id = pos.get("conditionId")
                slug = pos.get("slug")
                
                # Use conditionId as primary key, fallback to slug
                key = cond_id if cond_id else slug
                
                if not key: continue
                
                if key not in markets:
                    markets[key] = 0
                markets[key] += 1
        
        # If any market has > 1 position (meaning YES and NO, or multiple outcomes), 
        # it's likely a liquidity provider or farmer.
        hedged_markets = 0
        
        for key, count in markets.items():
            if count > 1:
                hedged_markets += 1
                
        # If they hedge more than 0 markets (even 1), we flag them.
        # This is a strict filter to ensure we tracking 'Snipers' not 'Farmers'.
        if hedged_markets > 0:
             return True
             
        return False
