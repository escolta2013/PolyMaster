from web3 import Web3
from eth_account import Account
from app.core.logging import logger
from app.engines.wallet.vault import vault
from typing import Dict, Any, Optional
from supabase import create_client, Client
from app.core.config import settings
from datetime import datetime

# USDC on Polygon (Native)
USDC_ADDRESS = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
USDC_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    }
]

class WalletManager:
    """
    Manages the lifecycle of proxy wallets: generation, storage, and retrieval.
    """
    
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.w3 = Web3(Web3.HTTPProvider(settings.POLYGON_RPC_URL))
        # Enable HD wallet features
        Account.enable_unaudited_hdwallet_features()

    def generate_proxy_wallet(self, user_id: str) -> Dict[str, str]:
        """
        Generates a new Ethereum account and stores it in Supabase for the user.
        """
        logger.info(f"Generating proxy wallet for user {user_id}")
        
        # Create new account
        acct = Account.create()
        address = acct.address
        private_key = acct.key.hex()
        
        # Encrypt private key
        encrypted_pk = vault.encrypt_key(private_key)
        
        # Store in DB
        try:
            data = {
                "user_id": user_id,
                "proxy_address": address,
                "encrypted_private_key": encrypted_pk,
                "created_at": datetime.utcnow().isoformat(),
                "balance_usdc": 0.0
            }
            self.supabase.table("user_wallets").insert(data).execute()
            
            logger.success(f"Proxy wallet generated and stored: {address}")
            return {"address": address}
        except Exception as e:
            logger.error(f"Failed to store proxy wallet for user {user_id}: {e}")
            raise e

    def get_onchain_balance(self, address: str) -> float:
        """Fetch the real USDC balance for an address on Polygon via Web3."""
        # --- FAKE BALANCE INJECTOR FOR SIMULATION ---
        if settings.COPY_SIMULATION:
            logger.info(f" [SIM] Injecting fake $100 balance for UI display on {address}")
            return 100.0
        # --------------------------------------------

        try:
            if not self.w3.is_connected():
                logger.warning("Web3 not connected, cannot fetch on-chain balance")
                return 0.0

            usdc = self.w3.eth.contract(
                address=Web3.to_checksum_address(USDC_ADDRESS), abi=USDC_ABI
            )
            raw = usdc.functions.balanceOf(Web3.to_checksum_address(address)).call()
            balance = raw / 10**6

            # Update Supabase Cache
            try:
                self.supabase.table("user_wallets").update({
                    "balance_usdc": float(round(balance, 2)),
                    "last_updated": datetime.utcnow().isoformat()
                }).eq("proxy_address", address).execute()
            except Exception as e:
                logger.debug(f"Could not update balance cache: {e}")

            return balance
        except Exception as e:
            logger.error(f"Error fetching on-chain balance for {address}: {e}")
            return 0.0

    def withdraw_usdc(self, user_id: str, target_address: str, amount: float) -> str:
        """
        Sends USDC from the user's proxy wallet to a target address.
        """
        pk = self.get_decrypted_key(user_id)
        if not pk: raise ValueError("No proxy wallet found")
        
        wallet = self.get_user_wallet(user_id)
        proxy_address = wallet["proxy_address"]
        
        # Connect
        acct = Account.from_key(pk)
        usdc = self.w3.eth.contract(address=Web3.to_checksum_address(USDC_ADDRESS), abi=USDC_ABI)
        
        # Check balance
        bal = self.get_onchain_balance(proxy_address)
        if bal < amount:
            raise ValueError(f"Insufficient balance: {bal} < {amount}")

        # Build transaction
        raw_amount = int(amount * 10**6)
        sender = acct.address
        nonce = self.w3.eth.get_transaction_count(sender)
        
        # EIP-1559 Gas Estimation
        from web3.exceptions import ContractLogicError
        try:
            # 1. Base transaction for estimation
            tx_data = usdc.functions.transfer(Web3.to_checksum_address(target_address), raw_amount)
            
            # 2. Estimate Gas
            estimated_gas = tx_data.estimate_gas({'from': sender})
            safe_gas_limit = int(estimated_gas * 1.2) # 20% buffer
            
            # 3. Get Fees
            history = self.w3.eth.fee_history(1, 'latest', reward_percentiles=[50])
            base_fee = history['baseFeePerGas'][0]
            priority_fee = self.w3.to_wei(30, 'gwei') # Aggressive priority for user withdrawals
            max_fee = base_fee + priority_fee
            
            # 4. Build EIP-1559 TX
            tx = tx_data.build_transaction({
                'chainId': 137,
                'gas': safe_gas_limit,
                'maxFeePerGas': max_fee,
                'maxPriorityFeePerGas': priority_fee,
                'nonce': nonce,
                'type': 2 
            })
            
            # Sign
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=pk)
            
            # Broadcast
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            logger.success(f"Withdrawal executed: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except ContractLogicError as e:
            logger.error(f"USDC Contract Error (Insufficent funds?): {e}")
            raise ValueError(f"Simulation failed: {e}")
        except Exception as e:
            logger.error(f"Withdrawal Failed: {e}")
            raise e

    def get_user_wallet(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves user's proxy wallet data from Supabase."""
        try:
            res = self.supabase.table("user_wallets").select("*").eq("user_id", user_id).single().execute()
            return res.data
        except Exception as e:
            logger.debug(f"User {user_id} has no proxy wallet or error: {e}")
            return None

    def get_decrypted_key(self, user_id: str) -> Optional[str]:
        """Retrieves and decrypts the private key for a user's proxy wallet."""
        wallet_data = self.get_user_wallet(user_id)
        if wallet_data and "encrypted_private_key" in wallet_data:
            return vault.decrypt_key(wallet_data["encrypted_private_key"])
        return None

wallet_manager = WalletManager()
