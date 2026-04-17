from web3 import Web3
from eth_account import Account
from app.core.logging import logger
from app.core.config import settings
from app.engines.wallet.manager import wallet_manager
from app.engines.wallet.vault import vault

# Polymarket CTF (Conditional Tokens Framework) - Polygon Mainnet
CTF_ADDRESS = "0x4D9706051241DCa1d1722A2a52ED1323f15CF923"
# USDC Bridged (Polymarket standard collateral)
USDC_BRIDGED = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

CTF_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "collateralToken", "type": "address"},
            {"name": "parentCollectionId", "type": "bytes32"},
            {"name": "conditionId", "type": "bytes32"},
            {"name": "indexSets", "type": "uint256[]"}
        ],
        "name": "redeemPositions",
        "outputs": [],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

class AutoRedeemer:
    """
    Automates the redemption of winning shares from resolved Polymarket markets.
    """

    def __init__(self):
        self.w3 = wallet_manager.w3
        self.ctf = self.w3.eth.contract(
            address=Web3.to_checksum_address(CTF_ADDRESS), 
            abi=CTF_ABI
        )

    async def redeem_market(self, condition_id: str, outcome: str):
        """
        Redeems winning shares for a specific market condition.
        outcome: 'YES' or 'NO'
        """
        if settings.COPY_SIMULATION:
            logger.info(f" [SIM] AutoRedeem: Market {condition_id[:10]}... would be redeemed (Outcome: {outcome})")
            return True

        # 1. Get credentials
        user_id = settings.AUTONOMOUS_USER_ID or "00000000-0000-0000-0000-000000000000"
        pk = wallet_manager.get_decrypted_key(user_id)
        if not pk:
            logger.error(f"AutoRedeem: No private key found for user {user_id}")
            return False

        acct = Account.from_key(pk)
        
        # 2. Prepare redemption parameters
        # IndexSets: [1] for YES (outcome 0), [2] for NO (outcome 1)
        # Note: In CTF binary markets, YES is index 0 (set 1), NO is index 1 (set 2)
        index_sets = [1] if outcome.upper() == "YES" else [2]
        
        try:
            logger.info(f"AutoRedeem: Executing on-chain redemption for {condition_id[:10]}... (Outcome: {outcome})")
            
            # 3. Build transaction
            nonce = self.w3.eth.get_transaction_count(acct.address)
            
            # Estimate gas with buffer
            collateral = Web3.to_checksum_address(USDC_BRIDGED)
            parent_collection = "0x" + "0" * 64 # NULL
            cond_id_bytes = Web3.to_bytes(hexstr=condition_id)
            
            tx_call = self.ctf.functions.redeemPositions(
                collateral,
                parent_collection,
                cond_id_bytes,
                index_sets
            )
            
            # EIP-1559 Transaction
            history = self.w3.eth.fee_history(1, 'latest', reward_percentiles=[50])
            base_fee = history['baseFeePerGas'][0]
            priority_fee = self.w3.to_wei(30, 'gwei')
            
            tx = tx_call.build_transaction({
                'chainId': 137,
                'gas': 150000, # Standard limit for redeem
                'maxFeePerGas': base_fee + priority_fee,
                'maxPriorityFeePerGas': priority_fee,
                'nonce': nonce,
                'from': acct.address,
                'type': 2
            })
            
            # 4. Sign and Send
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=pk)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.success(f"AutoRedeem Success! Tx: {tx_hash.hex()}")
            
            # Notify Telegram
            try:
                from app.services.telegram_bot import telegram
                await telegram.send_message(f"💰 **Ganancias Reclamadas!**\nMercado: `{condition_id[:12]}...`\nTx: [PolygonScan](https://polygonscan.com/tx/{tx_hash.hex()})")
            except Exception: pass
            
            return True
        except Exception as e:
            logger.error(f"AutoRedeem Failed for {condition_id}: {e}")
            return False

redeemer = AutoRedeemer()
