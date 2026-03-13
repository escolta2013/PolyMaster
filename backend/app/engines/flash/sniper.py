"""
Flash Engine: High-Frequency Blockchain Interaction Layer
Focus: Sub-second transaction broadcasting and Mempool monitoring.
"""

from app.core.config import settings
from app.core.logging import logger
from web3 import Web3, AsyncWeb3
from web3.providers import AsyncHTTPProvider
from web3.middleware import async_geth_poa_middleware
from eth_account import Account
import asyncio

# Standard CTF Exchange / Polymarket CTF Adapter ABI (Simplified for swap)
# We need the exact ABI for the Exchange or the Proxy
# For MVP, we will assume interaction with the CTFExchange contract directly.
CTF_EXCHANGE_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "returnAmount", "type": "uint256"},
            {"name": "poolId", "type": "bytes32"},
            {"name": "minTotalAmount", "type": "uint256"},
            # ... incomplete for now, we'll use a generic router call wrapper
        ],
        "name": "buy",
        "outputs": [],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

class FlashEngine:
    """
    Handles direct blockchain interactions bypassing the CLOB API for specific use cases
    like arb or sniping where CLOB might be slower or we're interacting with AMM pools directly.
    
    NOTE: Polymarket is primarily CLOB-based now. Direct blockchain interaction is mostly
    for deposits/withdrawals or emergency exits, or interacting with the underlying CTF contracts
    if liquidity exists in AMMs (like Uniswap/Balancer).
    """
    
    def __init__(self):
        self.w3 = AsyncWeb3(AsyncHTTPProvider(settings.FLASH_RPC_URL))
        # self.w3.middleware_onion.inject(async_geth_poa_middleware, layer=0) # For Polygon PoS
        self.gas_multiplier = settings.FAST_GAS_MULTIPLIER

    async def get_fast_gas(self):
        """Calculates aggressive gas price for priority inclusion."""
        base_fee = await self.w3.eth.gas_price
        # EIP-1559 logic would be better here
        return int(base_fee * self.gas_multiplier)

    async def estimate_nonce(self, address: str):
        return await self.w3.eth.get_transaction_count(address)

    async def snipe_transaction(self, tx_params: dict, private_key: str):
        """
        Signs and broadcasts a transaction immediately.
        """
        try:
            account = Account.from_key(private_key)
            
            # Fill gas and nonce if missing
            if 'nonce' not in tx_params:
                tx_params['nonce'] = await self.estimate_nonce(account.address)
            
            if 'gasPrice' not in tx_params and 'maxFeePerGas' not in tx_params:
                tx_params['gasPrice'] = await self.get_fast_gas()
                
            # Sign
            signed = self.w3.eth.account.sign_transaction(tx_params, private_key)
            
            # Broadcast
            tx_hash = await self.w3.eth.send_raw_transaction(signed.rawTransaction)
            logger.success(f"⚡ Flash Sniped: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Flash Snipe Failed: {e}")
            raise e

flash_engine = FlashEngine()
