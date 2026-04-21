from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "PolyMaster Engine"
    DEBUG: bool = False
    MASTER_API_KEY: str = "polymaster_admin_secret_99" # Default for dev
    
    # API URLs
    GAMMA_API_URL: str = "https://gamma-api.polymarket.com"
    DATA_API_URL: str = "https://data-api.polymarket.com"
    CLOB_API_URL: str = "https://clob.polymarket.com"
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Polymarket Authentication (Optional for tracking, required for Ghost)
    PK: Optional[str] = None
    CLOB_API_KEY: Optional[str] = None
    CLOB_SECRET: Optional[str] = None
    CLOB_PASSPHRASE: Optional[str] = None
    POLY_PROXY_ADDRESS: Optional[str] = None  # Set if using a Polymarket proxy wallet
    POLYMARKET_BUILDER_API_KEY: Optional[str] = None
    POLYMARKET_BUILDER_SECRET: Optional[str] = None
    POLYMARKET_BUILDER_PASSPHRASE: Optional[str] = None
    # AI / LLM Settings
    OPENAI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    AI_MODEL: str = "gpt-4o-mini"
    COUNCIL_MAX_DAILY_CALLS: int = 300     # Max council calls per day
    BALLDONTLIE_API_KEY: Optional[str] = None
    ODDS_API_KEY: str = ""
    COUNCIL_CONSENSUS_THRESHOLD: float = 0.66
    COUNCIL_DIVERG_THRESHOLD: float = 0.25
    COUNCIL_CQI_THRESHOLD: float = 0.08
    COUNCIL_KELLY_FRACTION: float = 0.1
    COUNCIL_CACHE_DEFAULT_TTL_HOURS: int = 4
    COUNCIL_CACHE_WHALE_DELTA: int = 2
    COUNCIL_CACHE_TOKEN_ESTIMATE: int = 4000
    
    # Engine Settings
    COPY_SIMULATION: bool = False
    MIN_ORDER_SIZE_USD: float = 5.0
    
    # Indexer (Discovery) Settings
    INDEXER_TARGET_TOTAL_MARKETS: int = 500
    INDEXER_BATCH_LIMIT: int = 100
    INDEXER_MIN_VOLUME: float = 100.0
    INDEXER_CHECK_COUNT_PAPER: int = 300
    INDEXER_CHECK_COUNT_LIVE: int = 150
    INDEXER_SEMAPHORE: int = 30
    INDEXER_MIN_PRICE: float = 0.15
    INDEXER_MAX_PRICE: float = 0.85
    INDEXER_MIN_DEPTH_LIVE: float = 10.0
    TRACKER_MARKET_SCAN_LIMIT: int = 3
    TRACKER_DUST_THRESHOLD: float = 1.0
    TRACKER_SLEEP_SEC: float = 0.5
    GRADE_WHALE_VOL: float = 1000000.0
    GRADE_WHALE_VOL: float = 1000000.0
    GRADE_WHALE_ROI: float = 0.15
    GRADE_SHARK_VOL: float = 100000.0
    GRADE_SHARK_ROI: float = 0.20
    GRADE_SHARK_WINRATE: float = 0.60
    GRADE_ORCA_ROI: float = 0.15
    GRADE_ORCA_WINRATE: float = 0.55
    GRADE_ORCA_TRADES: int = 30
    GHOST_TARGET_SPREAD: float = 0.02
    GHOST_BASE_SPREAD: float = 0.02
    GHOST_VOL_MULTIPLIER: float = 15.0
    GHOST_MAX_SPREAD: float = 0.10
    GHOST_ORDER_SIZE: float = 10.0
    NEH_ORDER_SIZE: float = 50.0
    NEH_SELL_PRICE: float = 0.85

    # Wallet Manager Settings
    WALLET_ENCRYPTION_KEY: Optional[str] = None
    POLYGON_RPC_URL: str = "https://polygon.llamarpc.com"
    ALCHEMY_RPC_URL: Optional[str] = None
    INFURA_RPC_URL: Optional[str] = None
    
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ADMIN_CHAT_ID: Optional[str] = None
    
    # Cluster Detector Settings
    CLUSTER_DEDUP_WINDOW_HOURS: int = 6
    CLUSTER_ACTIVITY_WINDOW_HOURS: int = 12
    CLUSTER_PRICE_LOW: float = 0.25
    CLUSTER_PRICE_HIGH: float = 0.75
    CLUSTER_WHALE_MAX_SPREAD: float = 0.15
    CLUSTER_BASE_CONFIDENCE: float = 0.60
    
    # Autonomous Director Settings (Phase 5)
    ENABLE_AUTONOMOUS_TRADING: bool = True
    AUTONOMOUS_CONFIDENCE_THRESHOLD: float = 0.68
    AUTONOMOUS_USER_ID: Optional[str] = None  # The UUID of the "System Proxy Wallet"
    AUTONOMOUS_MAX_SIZE: float = 20.0  # Max exposure per auto-trade
    AUTONOMOUS_MAX_MARKET_DURATION_HOURS: int = 48 # Skip markets ending > 48h from now
    AUTONOMOUS_CONFIDENCE_MAX: float = 0.999        # Cap for score in Kelly-like sizing
    AUTONOMOUS_MIN_WALLETS: int = 2 # Min wallets to trigger a cluster alert
    DIRECTOR_DEDUP_WINDOW_HOURS: int = 12
    DIRECTOR_PRICE_LIMIT_LOW_LIVE: float = 0.10
    DIRECTOR_PRICE_LIMIT_HIGH_LIVE: float = 0.90
    DIRECTOR_PRICE_LIMIT_LOW_PAPER: float = 0.05
    DIRECTOR_PRICE_LIMIT_HIGH_PAPER: float = 0.95
    DIRECTOR_IMMINENT_HOURS: int = 48
    DIRECTOR_SNIPING_WAIT_MINS: int = 60
    DIRECTOR_SNIPING_KILLZONE_MINS: int = 10
    DIRECTOR_MIN_EDGE_WHALE: float = 0.05
    DIRECTOR_PAPER_LOG_PRICE_DELTA: float = 0.02
    
    # Paper Trading Mode (Calibration Phase)
    # When enabled, the Director logs WOULD_EXECUTE decisions with relaxed spread
    # filters but never actually executes trades. Used to gather calibration data.
    # Set to False for Production.
    PAPER_TRADING_MODE: bool = False
    PAPER_TRADING_MAX_SPREAD: float = 0.15  # Stricter spread for production alignment
    PAPER_MIN_EDGE_NET: float = 0.05        # Min net edge after spread friction
    
    # Rewards Optimization Settings (The Grinder)
    ENABLE_REWARDS_FARMING: bool = False
    REWARDS_MAX_MARKETS: int = 3
    REWARDS_ORDER_SIZE: float = 100.0  # Size in shares to farm rewards
    GRINDER_TARGET_OFFSET: float = 0.03
    GRINDER_MAX_OFFSET: float = 0.045
    GRINDER_DRIFT_THRESHOLD: float = 0.04

    # Arbitrage Engine Settings
    ENABLE_ARBITRAGE: bool = False          # Enable the arbitrage scanner
    ARB_MAX_SUM: float = 0.985            # Trigger threshold: sum of prices must be < this
    ARB_MIN_EDGE_PCT: float = 0.01        # Min 1% edge after fees to execute
    ARB_MAX_BUDGET_PER_BUNDLE: float = 50.0  # Max USDC to deploy per arb opportunity
    ARB_DEDUP_WINDOW_SECONDS: int = 3600
    ARB_SCAN_LIMIT_BINARY: int = 100
    ARB_SCAN_LIMIT_BUNDLE: int = 50
    ARB_BATCH_SIZE: int = 10
    ARB_MIN_OUTCOMES: int = 3

    # NoFolio (Contrarian Sentiment) Settings
    ENABLE_NOFOLIO: bool = True           # Enable contrarian "buy NO on hype" strategy
    NOFOLIO_MAX_AI_SCORE: float = 0.40   # If Council score < this, YES is likely overvalued
    NOFOLIO_MIN_MARKET_PRICE: float = 0.70  # Market YES price must be > this (hype inflated)
    NOFOLIO_MAX_NO_PRICE: float = 0.40      # NO must be cheap (< 40 cents)

    # Weather Exploit Engine Settings
    ENABLE_WEATHER_EXP: bool = True       # Enable weather mispricing scanner
    WEATHER_SYNC_INTERVAL: int = 300      # Check weather data every 5 mins
    WEATHER_MIN_TEMP_DIFF: float = 1.0    # Execute if diff between NOAA and market is > 1.0°F/C (or threshold)
    WEATHER_MAX_BUDGET: float = 6.0       # Failsafe default: $6 USDC (min 5 required by CLOB)
    WEATHER_PRICE_BUFFER: float = 0.985   # Do not buy if price > this
    WEATHER_PHYSICAL_CERTAINTY_THRESHOLD: float = 0.2
    WEATHER_MAX_LAGGING_PRICE: float = 0.90
    WEATHER_MIN_MISPRICED_YES: float = 0.10
    WEATHER_SCAN_LIMIT: int = 50
    WEATHER_ENTRY_THRESHOLD_HIGH: float = 0.90
    WEATHER_ENTRY_THRESHOLD_LOW: float = 0.10
    WEATHER_API_KEY: str | None = None
    ARB_DEDUP_WINDOW: int = 3600 # Unified name

    # Portfolio Protection
    COPY_MAX_PER_TRADE: float = 20.0
    COPY_MAX_DAILY: float = 100.0
    GLOBAL_STOP_LOSS_PCT: float = 0.60
    GLOBAL_TAKE_PROFIT_PCT: float = 1.0
    EXCLUDED_MARKET_CATEGORIES: str = ""

    # Flash Engine Settings (Phase 4.3)
    FLASH_RPC_URL: str = "https://polygon-rpc.com" # Should be a private RPC for speed
    FAST_GAS_MULTIPLIER: float = 1.1 # 10% above market gas for priority
    
    # Infrastructure
    REDIS_URL: str = "redis://localhost:6379/0" 
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # Ignore extra variables in .env
        case_sensitive=False     # Case insensitive for ease of use
    )

settings = Settings()
