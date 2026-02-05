import logging
import requests
from typing import List, Dict, Any, Set

import json
from .clob_client import ClobClient

logger = logging.getLogger(__name__)

class PolymarketIndexer:
    """
    Fetches market data from Polymarket (Gamma API).
    """
    BASE_URL = "https://gamma-api.polymarket.com"

    def __init__(self):
        self.clob_client = ClobClient()

    def get_top_markets(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch top markets by volume to find where the whales are swimming.
        """
        try:
            # Polymarket Gamma API endpoint for markets
            url = f"{self.BASE_URL}/markets"
            params = {
                "limit": limit,
                "order": "volume",  # Gamma API uses 'order' for sorting field? Or 'sort'? 
                # Docs say: ?limit=10&offset=0&order=volume&ascending=false
                "ascending": "false",
                "closed": "false"
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data if isinstance(data, list) else []
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []

    def get_market_details(self, market_id: str) -> Dict[str, Any]:
        """
        Fetch details for a specific market.
        """
        try:
            url = f"{self.BASE_URL}/markets/{market_id}"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching market details for {market_id}: {e}")
            return {}

    def get_market_traders(self, market_id: str, min_order_size_usd: float = 500.0) -> List[str]:
        """
        Find active traders in a market by analyzing the orderbook.
        Since trades API requires auth, we extract addresses from large orders.
        
        NOTE: Orderbook entries don't contain wallet addresses in the public API.
        This is a limitation we'll work around by focusing on position analysis later.
        For now, we return an empty list and will populate via other means.
        """
        active_traders = set()
        
        try:
            details = self.get_market_details(market_id)
            
            # Extract clobTokenIds
            token_ids = []
            if "clobTokenIds" in details:
                token_ids = json.loads(details["clobTokenIds"]) if isinstance(details["clobTokenIds"], str) else details["clobTokenIds"]
            elif "tokens" in details:
                token_ids = [t.get("token_id") for t in details["tokens"] if t.get("token_id")]
            
            if not token_ids:
                logger.warning(f"No token IDs found for market {market_id}")
                return []

            # Fetch orderbook for each token
            for token_id in token_ids:
                book = self.clob_client.get_orderbook(token_id)
                
                # Analyze large orders (bids and asks)
                for bid in book.get("bids", []):
                    try:
                        price = float(bid.get("price", 0))
                        size = float(bid.get("size", 0))
                        order_value = price * size
                        
                        # If order is large enough, it's a potential whale
                        # NOTE: Orderbook doesn't expose wallet addresses publicly
                        # We'll need to use Data API to track known wallets instead
                        if order_value >= min_order_size_usd:
                            logger.debug(f"Large bid found: ${order_value:.2f}")
                    except (ValueError, TypeError):
                        continue
                
                for ask in book.get("asks", []):
                    try:
                        price = float(ask.get("price", 0))
                        size = float(ask.get("size", 0))
                        order_value = price * size
                        
                        if order_value >= min_order_size_usd:
                            logger.debug(f"Large ask found: ${order_value:.2f}")
                    except (ValueError, TypeError):
                        continue

        except Exception as e:
            logger.error(f"Error finding traders for market {market_id}: {e}")
            
        # For now, return empty list since orderbook doesn't expose addresses
        # We'll populate wallets via other discovery methods (e.g., known whales list)
        return list(active_traders)
    
    def discover_active_wallets(self, seed_addresses: List[str] = None) -> Set[str]:
        """
        Discover active wallets by checking positions of known addresses.
        This is a workaround since orderbook doesn't expose wallet addresses.
        
        Strategy:
        1. Start with a seed list of known whale addresses (if provided)
        2. Use Data API to check their positions
        3. Return addresses that have active positions
        
        For MVP, we'll use a small curated seed list.
        """
        discovered = set()
        
        # Default seed list of known Polymarket whales (example addresses)
        # In production, this would be populated from a database or external source
        if seed_addresses is None:
            seed_addresses = [
                # These are placeholder addresses - in production, populate with real whales
                # You can find these by monitoring high-volume markets or using block explorers
            ]
        
        for address in seed_addresses:
            try:
                positions = self.clob_client.get_user_positions(address)
                if positions and len(positions) > 0:
                    discovered.add(address)
                    logger.info(f"Found active wallet: {address[:10]}... with {len(positions)} positions")
            except Exception as e:
                logger.debug(f"Error checking wallet {address[:10]}...: {e}")
        
        return discovered

