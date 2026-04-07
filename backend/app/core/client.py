from loguru import logger
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from py_clob_client.client import ClobClient as PolymarketClobClient
from app.core.config import settings

class PolyClient:
    """
    Standardized ClobClient wrapper for all engines.
    Provides async-ready access to Polymarket APIs and the official SDK.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.host = settings.CLOB_API_URL
        self.data_api = settings.DATA_API_URL
        self.gamma_api = settings.GAMMA_API_URL
        
        pk = settings.PK
        chain_id = 137
        
        if pk:
            logger.info("Initializing fully authenticated PolyClient")
            # Step 1: Create temp client to derive or use creds
            is_proxy = hasattr(settings, 'POLY_PROXY_ADDRESS') and settings.POLY_PROXY_ADDRESS
            sig_type = 2 if is_proxy else 1
            funder = settings.POLY_PROXY_ADDRESS if is_proxy else None
            
            try:
                temp_client = PolymarketClobClient(
                    host=self.host,
                    key=pk,
                    chain_id=chain_id,
                    signature_type=sig_type,
                    funder=funder
                )
                
                # Use provided creds if they exist, otherwise derive
                if settings.CLOB_API_KEY and settings.CLOB_SECRET:
                    from py_clob_client.clob_types import ApiCreds
                    clob_key = settings.CLOB_API_KEY.replace('\r', '').replace('\n', '').strip(' "\'')
                    clob_sec = settings.CLOB_SECRET.replace('\r', '').replace('\n', '').strip(' "\'')
                    clob_pass = settings.CLOB_PASSPHRASE.replace('\r', '').replace('\n', '').strip(' "\'') if settings.CLOB_PASSPHRASE else ""
                    creds = ApiCreds(clob_key, clob_sec, clob_pass)
                    logger.info("Using provided API credentials")
                else:
                    logger.info("Deriving API credentials from PK...")
                    creds = temp_client.create_or_derive_api_creds()
                
                self.sdk = PolymarketClobClient(
                    host=self.host,
                    key=pk,
                    chain_id=chain_id,
                    signature_type=sig_type,
                    funder=funder,
                    creds=creds
                )
                logger.success("Authenticated SDK Client Ready")
            except Exception as e:
                logger.warning(f"Authentication failed: {e}. Falling back to limited mode.")
                self.sdk = temp_client
        else:
            logger.info("Initializing Read-Only PolyClient")
            self.sdk = PolymarketClobClient(host=self.host, chain_id=chain_id)

    async def get_authenticated_client(self, pk: str) -> PolymarketClobClient:
        """
        Creates a temporary authenticated ClobClient for a specific private key.
        Used for executing trades on behalf of proxy wallets.
        """
        try:
            # We use signature_type 1 (EOA) for proxy wallets
            client = PolymarketClobClient(
                host=self.host,
                key=pk,
                chain_id=137,
                signature_type=1
            )
            # Derive API creds (L2 authentication)
            # In a production scenario, we might want to cache these creds in the DB
            creds = client.create_or_derive_api_creds()
            client.set_api_creds(creds)
            return client
        except Exception as e:
            logger.error(f"Failed to create authenticated client: {e}")
            raise e

    # --- Async Proxies for Public APIs ---

    async def get_user_positions(self, address: str) -> List[Dict]:
        async with httpx.AsyncClient() as client:
            for attempt in range(2): # Try twice
                try:
                    resp = await client.get(
                        f"{self.data_api}/positions", 
                        params={"user": address}, 
                        timeout=20.0
                    )
                    if resp.status_code == 200:
                        return resp.json()
                    elif resp.status_code == 404:
                        return [] # Wallet has no positions
                    
                    logger.warning(f"Data API returned {resp.status_code} for {address} (Attempt {attempt+1})")
                except Exception as e:
                    if attempt == 1: # Last attempt failed
                        logger.error(f"Error fetching positions for {address} after 2 attempts: {e}")
                    else:
                        await asyncio.sleep(1) # Wait before retry
            return []

    async def get_orderbook(self, token_id: str) -> Dict[str, Any]:
        """
        Fetches the orderbook and calculates Price Intelligence metrics.
        Translations from poly-trading-skills patterns:
        - Best Ask: Lowest price to buy instantly
        - Best Bid: Highest price to sell instantly
        - Spread: Difference between ASK and BID
        """
        try:
            # SDK call is sync
            book = self.sdk.get_order_book(token_id)
            
            bids = [{"price": float(b.price), "size": float(b.size)} for b in book.bids]
            asks = [{"price": float(a.price), "size": float(a.size)} for a in book.asks]
            
            best_bid = bids[0]["price"] if bids else None
            best_ask = asks[0]["price"] if asks else None
            
            spread = 0.0
            midpoint = 0.5
            
            if best_bid and best_ask:
                spread = best_ask - best_bid
                midpoint = (best_ask + best_bid) / 2
            elif best_bid:
                midpoint = best_bid
            elif best_ask:
                midpoint = best_ask

            return {
                "bids": bids,
                "asks": asks,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": round(spread, 4),
                "midpoint": round(midpoint, 4),
                "bid_depth": sum(b["size"] for b in bids[:5]), # Top 5 levels depth
                "ask_depth": sum(a["size"] for a in asks[:5]),
            }
        except Exception as e:
            err_msg = str(e)
            if "404" in err_msg or "No orderbook exists" in err_msg:
                # This is a common occurrence for settled or inactive markets
                logger.debug(f"Orderbook not found for {token_id}. Market may be settled or non-CLOB.")
            else:
                # Truncate error message to avoid logging huge HTML pages if API is down
                clean_msg = err_msg[:100] + ("..." if len(err_msg) > 100 else "")
                logger.info(f"Price metadata missing for {token_id}: {clean_msg}")
            
            # Silent sentinel return for cleaner logs
            return {
                "bids": [], "asks": [], 
                "best_bid": None, "best_ask": None, 
                "spread": None, "midpoint": None,
                "bid_depth": 0, "ask_depth": 0,
                "error": True
            }

    async def get_midpoint(self, token_id: str) -> float:
        try:
            mid_data = self.sdk.get_midpoint(token_id)
            return float(mid_data.get('mid', 0.5))
        except:
            return 0.5

    async def get_market_volatility(self, token_id: str, samples: int = 5) -> float:
        """
        Calculates price volatility using standard deviation of recent midpoints.
        Pattern from poly-trading-skills Adaptive Spread strategy.
        """
        try:
            prices = []
            for _ in range(samples):
                prices.append(await self.get_midpoint(token_id))
                await asyncio.sleep(0.5) # Fast sampling
            
            if not prices:
                return 0.0
                
            mean = sum(prices) / len(prices)
            variance = sum((p - mean) ** 2 for p in prices) / len(prices)
            volatility = variance ** 0.5
            
            logger.debug(f"Volatility for {token_id}: {volatility:.6f} (Mean: {mean:.4f})")
            return volatility
        except Exception as e:
            logger.error(f"Error calculating volatility for {token_id}: {e}")
            return 0.0
