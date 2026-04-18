import os
import time
import requests
import asyncio
from datetime import datetime
from eth_abi import encode as eth_encode
from eth_utils import keccak

# Relayer imports
from py_builder_relayer_client.client import RelayClient
from py_builder_relayer_client.models import RelayerTxType, OperationType, SafeTransaction
from py_builder_signing_sdk.config import BuilderConfig, BuilderApiKeyCreds

from app.core.logging import logger
from app.core.config import settings
from app.engines.wallet.manager import wallet_manager

# Contract addresses (Polygon)
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CTF_ADDRESS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
NEG_RISK_ADAPTER = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"

# Function selectors (pre-computed)
REDEEM_SELECTOR = keccak(text="redeemPositions(address,bytes32,bytes32,uint256[])")[:4]
NEG_RISK_REDEEM_SELECTOR = keccak(text="redeemPositions(bytes32,uint256[])")[:4]

RELAYER_RETRY_WAIT = 60  # seconds to wait on rate limit before retrying


class AutoRedeemer:
    """
    Automates the redemption of winning shares from resolved Polymarket markets.
    Upgraded to use Polymarket's Official Relayer for proxy wallets (Gasless L1 interactions).
    """

    def __init__(self):
        pass

    async def redeem_all_resolved(self) -> int:
        """
        Scans checking for ALL redeemable positions and reclaims USDC.
        Returns the number of markets successfully redeemed.
        """
        if settings.COPY_SIMULATION:
            logger.info(" [SIM] AutoRedeem: Skipping redemption in simulation mode.")
            return 0

        funder_address = settings.POLY_PROXY_ADDRESS
        builder_api_key = settings.POLYMARKET_BUILDER_API_KEY
        builder_secret = settings.POLYMARKET_BUILDER_SECRET
        builder_passphrase = settings.POLYMARKET_BUILDER_PASSPHRASE
        
        user_id = settings.AUTONOMOUS_USER_ID or "00000000-0000-0000-0000-000000000000"
        private_key = wallet_manager.get_decrypted_key(user_id)
        
        if not private_key:
            logger.error("AutoRedeem: No private key found.")
            return 0

        if not funder_address or not builder_api_key:
            logger.error("AutoRedeem: Cannot redeem. Missing POLY_PROXY_ADDRESS or POLYMARKET_BUILDER_API_KEY")
            return 0

        # Assuming email account (Proxy wallet) as is standard for most automated Polymarket API bots
        signature_type = 1 
        wallet_type = RelayerTxType.PROXY if signature_type == 1 else RelayerTxType.SAFE

        logger.info("AutoRedeem: Connecting to Polymarket Relayer...")
        try:
            client = RelayClient(
                "https://relayer-v2.polymarket.com",
                chain_id=137,
                private_key=private_key,
                builder_config=BuilderConfig(
                    local_builder_creds=BuilderApiKeyCreds(
                        key=builder_api_key,
                        secret=builder_secret,
                        passphrase=builder_passphrase,
                    )
                ),
                relay_tx_type=wallet_type,
            )
        except Exception as e:
            logger.error(f"AutoRedeem: Failed to initialize RelayClient: {e}")
            return 0

        logger.info("AutoRedeem: Fetching redeemable positions from Data API...")
        try:
            response = requests.get(
                "https://data-api.polymarket.com/positions",
                params={"user": funder_address, "redeemable": "true", "sizeThreshold": 0},
                timeout=15,
            )
            if response.status_code in (429, 1015):
                logger.warning(f"AutoRedeem: Rate limited. Waiting {RELAYER_RETRY_WAIT}s...")
                await asyncio.sleep(RELAYER_RETRY_WAIT)
                response = requests.get(
                    "https://data-api.polymarket.com/positions",
                    params={"user": funder_address, "redeemable": "true", "sizeThreshold": 0},
                )
            
            if response.status_code != 200:
                logger.error(f"AutoRedeem: Data API returned HTTP {response.status_code}")
                return 0
                
            positions = response.json()
        except Exception as e:
            logger.error(f"AutoRedeem: Failed to fetch positions: {e}")
            return 0

        # The API may still return positions with size 0 after redemption. Skip them.
        positions = [p for p in positions if float(p.get("size", 0)) > 0]

        if not positions:
            logger.info("AutoRedeem: No positions to redeem.")
            return 0

        logger.info(f"AutoRedeem: Found {len(positions)} redeemable positions.")
        
        redeemed = 0
        from app.services.telegram_bot import telegram

        for pos in positions:
            cid = pos.get("conditionId", pos.get("condition_id", ""))
            if not cid:
                continue
            if not cid.startswith("0x"):
                cid = "0x" + cid
                
            market = pos.get("title", cid[:12])
            logger.info(f"AutoRedeem: Attempting to redeem market: {market}")

            try:
                condition_bytes = bytes.fromhex(cid[2:])
                neg_risk = pos.get("negativeRisk")

                if neg_risk is True:
                    size_raw = int(float(pos.get("size", 0)) * 1e6)
                    outcome_index = int(pos.get("outcomeIndex", 0))
                    amounts = [0, 0]
                    amounts[outcome_index] = size_raw

                    args = eth_encode(["bytes32", "uint256[]"], [condition_bytes, amounts])
                    txn = SafeTransaction(
                        to=NEG_RISK_ADAPTER,
                        operation=OperationType.Call,
                        data="0x" + (NEG_RISK_REDEEM_SELECTOR + args).hex(),
                        value="0",
                    )

                elif neg_risk is False:
                    args = eth_encode(
                        ["address", "bytes32", "bytes32", "uint256[]"],
                        [USDC_ADDRESS, b"\\x00" * 32, condition_bytes, [1, 2]],
                    )
                    txn = SafeTransaction(
                        to=CTF_ADDRESS,
                        operation=OperationType.Call,
                        data="0x" + (REDEEM_SELECTOR + args).hex(),
                        value="0",
                    )
                else:
                    logger.warning(f"AutoRedeem: Skipping {market}: unsupported market type (negativeRisk={neg_risk!r})")
                    continue

                try:
                    # Offload blocking synchronous relayer wait to an asyncio thread
                    # resp.wait() can take 2-5 seconds
                    def execute_and_wait():
                        resp = client.execute([txn], f"redeem {cid[:12]}")
                        resp.wait()
                        
                    await asyncio.to_thread(execute_and_wait)
                    
                except Exception as relay_err:
                    status = getattr(relay_err, "status_code", None)
                    if status in (429, 1015):
                        logger.warning(f"AutoRedeem: Relayer rate limited (HTTP {status}), waiting {RELAYER_RETRY_WAIT}s...")
                        await asyncio.sleep(RELAYER_RETRY_WAIT)
                        
                        def execute_and_wait_retry():
                            resp = client.execute([txn], f"redeem {cid[:12]}")
                            resp.wait()
                        await asyncio.to_thread(execute_and_wait_retry)
                    else:
                        raise relay_err

                redeemed += 1
                logger.success(f"AutoRedeem: Successfully redeemed {market}")
                
                try:
                    await telegram.notify(f"💰 **Ganancias Reclamadas Automáticamente!**\\nMercado: <code>{market[:50]}...</code>\\nLas ganancias ya están libes en tu saldo USDC.")
                except Exception:
                    pass

            except Exception as e:
                logger.error(f"AutoRedeem: Failed to redeem {market}: {e}")

        logger.info(f"AutoRedeem: Finished. Redeemed {redeemed}/{len(positions)} positions.")
        return redeemed


redeemer = AutoRedeemer()
