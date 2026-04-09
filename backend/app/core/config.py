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
    
    # AI / LLM Settings
    OPENAI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    AI_MODEL: str = "gpt-4o-mini"
    COUNCIL_MAX_DAILY_CALLS: int = 300     # Max council calls per day
    BALLDONTLIE_API_KEY: Optional[str] = None
    ODDS_API_KEY: str = ""
    
    # Engine Settings
    COPY_SIMULATION: bool = True
    MIN_ORDER_SIZE_USD: float = 500.0
    
    # Wallet Manager Settings
    WALLET_ENCRYPTION_KEY: Optional[str] = None
    POLYGON_RPC_URL: str = "https://polygon.llamarpc.com"
    
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ADMIN_CHAT_ID: Optional[str] = None
    
    # Autonomous Director Settings (Phase 5)
    ENABLE_AUTONOMOUS_TRADING: bool = False
    AUTONOMOUS_CONFIDENCE_THRESHOLD: float = 0.85
    AUTONOMOUS_USER_ID: Optional[str] = None  # The UUID of the "System Proxy Wallet"
    AUTONOMOUS_MAX_SIZE: float = 50.0  # Max exposure per auto-trade
    AUTONOMOUS_MAX_MARKET_DURATION_HOURS: int = 96 # Skip markets ending > 96h from now
    AUTONOMOUS_CONFIDENCE_MAX: float = 0.75        # Cap for score in Kelly-like sizing
    AUTONOMOUS_MIN_WALLETS: int = 2 # Min wallets to trigger a cluster alert
    
    # Paper Trading Mode (Calibration Phase)
    # When enabled, the Director logs WOULD_EXECUTE decisions with relaxed spread
    # filters but never actually executes trades. Used to gather calibration data.
    PAPER_TRADING_MODE: bool = True
    PAPER_TRADING_MAX_SPREAD: float = 0.15  # Stricter spread for production alignment
    PAPER_MIN_EDGE_NET: float = 0.05        # Min net edge after spread friction
    
    # Rewards Optimization Settings
    ENABLE_REWARDS_FARMING: bool = False
    REWARDS_MAX_MARKETS: int = 3
    REWARDS_ORDER_SIZE: float = 100.0  # Size in shares to farm rewards

    # Arbitrage Engine Settings
    ENABLE_ARBITRAGE: bool = True          # Enable the arbitrage scanner
    ARB_MAX_SUM: float = 0.985            # Trigger threshold: sum of prices must be < this
    ARB_MIN_EDGE_PCT: float = 0.01        # Min 1% edge after fees to execute
    ARB_MAX_BUDGET_PER_BUNDLE: float = 50.0  # Max USDC to deploy per arb opportunity

    # NoFolio (Contrarian Sentiment) Settings
    ENABLE_NOFOLIO: bool = True           # Enable contrarian "buy NO on hype" strategy
    NOFOLIO_MAX_AI_SCORE: float = 0.40   # If Council score < this, YES is likely overvalued
    NOFOLIO_MIN_MARKET_PRICE: float = 0.70  # Market YES price must be > this (hype inflated)

    # Weather Exploit Engine Settings
    ENABLE_WEATHER_EXP: bool = True       # Enable weather mispricing scanner
    WEATHER_SYNC_INTERVAL: int = 300      # Check weather data every 5 mins
    WEATHER_MIN_TEMP_DIFF: float = 1.0    # Execute if diff between NOAA and market is > 1.0°F/C (or threshold)
    WEATHER_MAX_BUDGET: float = 50.0      # Max USDC per weather trade
    WEATHER_PRICE_BUFFER: float = 0.985   # Do not buy if price > this

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
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
