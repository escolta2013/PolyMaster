from loguru import logger
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from py_clob_client.client import ClobClient as PolymarketClobClient
from eth_account import Account
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
            from web3 import Web3
            is_proxy = hasattr(settings, 'POLY_PROXY_ADDRESS') and settings.POLY_PROXY_ADDRESS

            # ── Signature Type Selection ──────────────────────────────────────
            # Ensure addresses are checksummed to avoid the error seen in logs
            if is_proxy:
                sig_type = 2  # GNOSIS_SAFE/POLY_PROXY  
                funder = Web3.to_checksum_address(Account.from_key(pk).address)
                logger.info(f"Proxy wallet detected. Using sig_type=2 (GNOSIS_SAFE) with funder={funder}")      
            else:
                sig_type = 0  # EOA
                funder = None
                logger.info("No proxy wallet. Using sig_type=0 (EOA)")

            # Helper: build API creds from .env or derive them
            def _get_creds(client_instance):
                if settings.CLOB_API_KEY and settings.CLOB_SECRET:
                    from py_clob_client.clob_types import ApiCreds
                    clob_key = settings.CLOB_API_KEY.replace('\r', '').replace('\n', '').strip(' "\'')
                    clob_sec = settings.CLOB_SECRET.replace('\r', '').replace('\n', '').strip(' "\'')
                    clob_pass = settings.CLOB_PASSPHRASE.replace('\r', '').replace('\n', '').strip(' "\'') if settings.CLOB_PASSPHRASE else ""
                    logger.info("Using provided API credentials")
                    return ApiCreds(clob_key, clob_sec, clob_pass)
                else:
                    logger.info("Deriving API credentials from PK...")
                    return client_instance.create_or_derive_api_creds()

            try:
                # Removal of incompatible proxy_address for current SDK version
                temp_client = PolymarketClobClient(     
                    host=self.host,
                    key=pk,
                    chain_id=chain_id,
                    signature_type=sig_type,
                    funder=funder
                )
                creds = _get_creds(temp_client)

                self.sdk = PolymarketClobClient(        
                    host=self.host,
                    key=pk,
                    chain_id=chain_id,
                    signature_type=sig_type,
                    funder=funder,
                    creds=creds
                )
                logger.success(f"Authenticated SDK Client Ready (Type {sig_type}, funder={funder})")
            except Exception as e:
                # ── Fallback Chain ─────────────────────────────────────────
                alt_sig_type = 0 if sig_type in (1, 2) else 2
                alt_funder = None if alt_sig_type == 0 else (funder or settings.POLY_PROXY_ADDRESS if hasattr(settings, 'POLY_PROXY_ADDRESS') else None)
                logger.warning(f"Authentication failed with Type {sig_type}: {e}. Trying Type {alt_sig_type} fallback...")
                try:
                    temp_client = PolymarketClobClient( 
                        host=self.host, key=pk, chain_id=chain_id,
                        signature_type=alt_sig_type, funder=alt_funder
                    )
                    creds = _get_creds(temp_client)     
                    self.sdk = PolymarketClobClient(    
                        host=self.host, key=pk, chain_id=chain_id,
                        signature_type=alt_sig_type, funder=alt_funder,
                        creds=creds
                    )
                    logger.success(f"Authenticated SDK Client Ready (Type {alt_sig_type} FALLBACK, funder={alt_funder})")
                except Exception as e2:
                    logger.error(f"All authentication attempts failed: {e2}")
                    self.sdk = None
        else:
            logger.info("Initializing Read-Only PolyClient")
            self.sdk = PolymarketClobClient(host=self.host, chain_id=chain_id)

    async def get_authenticated_client(self, pk: str) -> PolymarketClobClient:
        """
        Creates a temporary authenticated ClobClient for a specific private key.
        Used for executing trades on behalf of proxy wallets.
        """
        from web3 import Web3
        is_proxy = hasattr(settings, 'POLY_PROXY_ADDRESS') and settings.POLY_PROXY_ADDRESS
        sig_type = 2 if is_proxy else 0
        funder = Web3.to_checksum_address(Account.from_key(pk).address) if is_proxy else None

        try:
            client = PolymarketClobClient(
                host=self.host,
                key=pk,
                chain_id=137,
                signature_type=sig_type,
                funder=funder
            )
            creds = client.create_or_derive_api_creds() 
            client.set_api_creds(creds)
            return client
        except Exception as e:
            # Fallback for EOA if sig_type=2 failed     
            if sig_type in (1, 2):
                logger.warning(f"Failed to create authenticated client as Proxy: {e}. Retrying as EOA...")      
                try:
                    client = PolymarketClobClient(host=self.host, key=pk, chain_id=137, signature_type=0)       
                    creds = client.create_or_derive_api_creds()
                    client.set_api_creds(creds)
                    return client
                except Exception as e2:
                    logger.error(f"Failed all authenticated client attempts: {e2}")
                    raise e2
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
