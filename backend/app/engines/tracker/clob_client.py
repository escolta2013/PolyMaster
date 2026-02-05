import logging
import requests
from typing import List, Dict, Any
from py_clob_client.client import ClobClient as PolymarketClobClient

logger = logging.getLogger(__name__)

class ClobClient:
    """
    Wrapper for Polymarket CLOB and Data API interactions.
    Uses the official py-clob-client SDK for orderbook access.
    """
    
    def __init__(self):
        self.CLOB_HOST = "https://clob.polymarket.com"
        self.DATA_API = "https://data-api.polymarket.com"
        self.GAMMA_API = "https://gamma-api.polymarket.com"
        
        # Try to load API credentials from environment
        import os
        private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
        api_key = os.getenv("POLYMARKET_API_KEY")
        api_secret = os.getenv("POLYMARKET_API_SECRET")
        passphrase = os.getenv("POLYMARKET_API_PASSPHRASE")
        chain_id = int(os.getenv("POLYMARKET_CHAIN_ID", "137"))
        
        # Initialize SDK client
        if private_key and private_key != "your_private_key_here":
            # Authenticated client (can access trades, place orders, etc.)
            logger.info("Initializing authenticated CLOB client")
            
            # Step 1: Create temporary client to derive L2 credentials
            temp_client = PolymarketClobClient(
                host=self.CLOB_HOST,
                key=private_key,
                chain_id=chain_id,
                signature_type=1  # 1 = Email/Magic wallet, 0 = EOA, 2 = Browser proxy
            )
            
            # Step 2: Derive L2 API credentials from private key
            try:
                logger.info("Deriving L2 API credentials from private key...")
                creds = temp_client.create_or_derive_api_creds()
                logger.info(f"API credentials derived: {creds.api_key[:10]}...")
                
                # Step 3: Create new client with both private key AND credentials
                # This is the key - credentials must be passed during initialization
                self.sdk_client = PolymarketClobClient(
                    host=self.CLOB_HOST,
                    key=private_key,
                    chain_id=chain_id,
                    signature_type=1,
                    creds=creds  # Pass derived credentials here
                )
                logger.info("Authenticated client ready (L1 + L2)")
            except Exception as e:
                logger.warning(f"Could not derive API credentials: {e}")
                logger.info("Falling back to L1-only authentication")
                self.sdk_client = temp_client
        else:
            # Read-only client (orderbook, public data only)
            logger.info("Initializing read-only CLOB client (no auth)")
            self.sdk_client = PolymarketClobClient(
                host=self.CLOB_HOST,
                chain_id=chain_id
            )
    
    def get_orderbook(self, token_id: str) -> Dict[str, Any]:
        """
        Get the current orderbook for a specific token using the SDK.
        Returns bids and asks with price/size information.
        """
        try:
            book = self.sdk_client.get_order_book(token_id)
            
            # Convert SDK response to dict format
            return {
                "bids": [{"price": bid.price, "size": bid.size} for bid in book.bids],
                "asks": [{"price": ask.price, "size": ask.size} for ask in book.asks],
                "timestamp": book.timestamp if hasattr(book, 'timestamp') else None
            }
        except Exception as e:
            logger.error(f"Error fetching orderbook for token {token_id}: {e}")
            return {"bids": [], "asks": []}
    
    def get_user_positions(self, wallet_address: str) -> List[Dict[str, Any]]:
        """
        Fetch all positions for a wallet address from the Data API.
        This is PUBLIC and does NOT require authentication.
        """
        try:
            url = f"{self.DATA_API}/positions"
            params = {"user": wallet_address}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching positions for {wallet_address}: {e}")
            return []
    
    def get_market_trades(self, asset_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch recent trades for a specific asset (token_id).
        Now uses SDK method with TradeParams for proper authentication.
        """
        try:
            # Import TradeParams for proper SDK usage
            from py_clob_client.clob_types import TradeParams
            
            # Create TradeParams object - SDK expects this, not a raw string
            params = TradeParams(market=asset_id)
            
            # Use SDK method - it handles auth headers automatically
            trades = self.sdk_client.get_trades(params)
            
            # Convert SDK response to list of dicts
            if trades and hasattr(trades, '__iter__'):
                result = []
                for trade in list(trades)[:limit]:
                    # Convert trade object to dict if needed
                    if hasattr(trade, '__dict__'):
                        result.append(vars(trade))
                    elif isinstance(trade, dict):
                        result.append(trade)
                return result
            
            return []
        except Exception as e:
            logger.warning(f"Error fetching trades for {asset_id[:20]}...: {e}")
            return []
    
    def get_sampling(self, token_id: str = None) -> Dict[str, Any]:
        """
        Get simplified market data (mid-price, spread) using SDK methods.
        """
        try:
            if not token_id:
                return {}
            
            mid = self.sdk_client.get_midpoint(token_id)
            spread = self.sdk_client.get_spread(token_id)
            
            return {
                "mid": mid.get("mid"),
                "spread": spread.get("spread")
            }
        except Exception as e:
            logger.error(f"Error fetching sampling for token {token_id}: {e}")
            return {}
