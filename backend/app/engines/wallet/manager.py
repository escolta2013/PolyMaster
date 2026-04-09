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

# Cadena de fallback de RPCs de Polygon.
# Si uno falla con 429, el sistema pasa automáticamente al siguiente.
_RPC_LIST = [
    getattr(settings, "POLYGON_RPC_URL", None) or "https://polygon-rpc.com/",
    "https://polygon-rpc.com/",
    "https://rpc.ankr.com/polygon",
    "https://polygon.llamarpc.com",
    "https://1rpc.io/matic",
]
# Remover None y duplicados manteniendo orden
_seen_rpcs: set = set()
_RPC_LIST = [r for r in _RPC_LIST if r and r not in _seen_rpcs and not _seen_rpcs.add(r)]


class WalletManager:
    """
    Manages the lifecycle of proxy wallets: generation, storage, and retrieval.
    """

    
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self._rpc_index = 0
        self.w3 = Web3(Web3.HTTPProvider(_RPC_LIST[0]))
        # Enable HD wallet features
        Account.enable_unaudited_hdwallet_features()

    def _rotate_rpc(self, failed_url: str):
        """Rota al siguiente RPC en la lista y notifica via Telegram."""
        self._rpc_index = (self._rpc_index + 1) % len(_RPC_LIST)
        new_url = _RPC_LIST[self._rpc_index]
        logger.warning(f"RPC Failover: '{failed_url}' bloqueado. Rotando a '{new_url}'")
        self.w3 = Web3(Web3.HTTPProvider(new_url))
        try:
            from app.services.telegram_bot import telegram
            telegram.notify_sync(f"🔄 RPC Failover: {failed_url} bloqueado (429). Ahora usando {new_url}")
        except Exception:
            pass

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
        """Fetch the real USDC balance on Polygon con failover automático de RPC."""
        # --- FAKE BALANCE INJECTOR FOR SIMULATION ---
        if settings.COPY_SIMULATION:
            logger.info(f" [SIM] Injecting fake $100 balance for UI display on {address}")
            return 100.0
        # --------------------------------------------
        
        # Intenta con cada RPC disponible antes de rendirse
        for attempt in range(len(_RPC_LIST)):
            current_url = _RPC_LIST[self._rpc_index]
            try:
                return self._fetch_balance(address)
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "Too Many Requests" in err_msg or "Connection" in err_msg:
                    self._rotate_rpc(current_url)
                else:
                    # Error no relacionado con el RPC (ej. dirección inválida) — no rotar
                    logger.error(f"Error fetching balance for {address}: {err_msg}")
                    return 0.0
        
        # Todos los RPCs fallaron
        logger.error(f"Todos los RPCs de Polygon fallaron para {address}")
        try:
            from app.services.telegram_bot import telegram
            telegram.notify_sync("🚨 CRÍTICO: Todos los nodos RPC de Polygon están caídos o limitados. Balance no disponible.")
        except Exception:
            pass
        return 0.0

    def _fetch_balance(self, address: str) -> float:
        """Llamada directa al RPC activo para obtener el balance. Lanza excepción si falla."""
        USDC_ADDRESS = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"

        try:
            if not self.w3.is_connected():
                raise ConnectionError("Web3 not connected to RPC")

            # Native USDC
            usdc_native = self.w3.eth.contract(
                address=Web3.to_checksum_address("0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"), abi=USDC_ABI
            )
            bal_n = usdc_native.functions.balanceOf(Web3.to_checksum_address(address)).call()
            
            # Bridged USDC.e (which most Polymarket wallets use)
            usdc_bridged = self.w3.eth.contract(
                address=Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"), abi=USDC_ABI
            )
            bal_b = usdc_bridged.functions.balanceOf(Web3.to_checksum_address(address)).call()

            balance = (bal_n + bal_b) / 10**6

            # Update Supabase Cache
            try:
                self.supabase.table("user_wallets").update({
                    "balance_usdc": float(round(balance, 2)),
                    "last_updated": datetime.utcnow().isoformat()
                }).eq("proxy_address", address).execute()
            except Exception as e:
                logger.debug(f"Could not update balance cache: {e}")

            return balance
        except Exception:
            # Re-raise para que get_onchain_balance pueda rotar el RPC
            raise

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
