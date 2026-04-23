"""
Status Router — Dashboard API
Búsqueda exhaustiva de saldo para resolver el problema de los $11.00.
"""

import os
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter
from loguru import logger
from eth_account import Account
from app.engines.wallet.manager import wallet_manager   
from app.core.config import settings
from web3 import Web3

router = APIRouter(prefix="/api", tags=["status"])

def _get_supabase():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

@router.get("/status")
def get_status():
    from app.core.client import PolyClient
    from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
    from py_clob_client.client import ClobClient
    
    # ── 1. Saldo On-Chain (Wallet) ──
    main_addr = Web3.to_checksum_address(Account.from_key(settings.PK).address)
    bal_main = wallet_manager.get_onchain_balance(main_addr)
    
    proxy_addr = getattr(settings, 'POLY_PROXY_ADDRESS', None)
    bal_proxy = 0.0
    if proxy_addr:
        proxy_addr = Web3.to_checksum_address(proxy_addr)
        bal_proxy = wallet_manager.get_onchain_balance(proxy_addr)
    
    # ── 2. Saldo en el Exchange (CLOB) ──
    clob_bal = 0.0
    try:
        p_client = PolyClient.get_instance()
        if p_client and p_client.sdk:
            # Intento A: Lo que el SDK diga (usando Proxy como Funder si está configurada)
            try:
                res = p_client.sdk.get_balance_allowance(BalanceAllowanceParams(asset_type=AssetType.COLLATERAL))
                clob_bal = float(res.get("balance", 0)) / 10**6
                logger.debug(f"[BalanceSync] SDK Result: {res}")
            except Exception as e:
                logger.error(f"[BalanceSync] SDK Error: {e}")

            # Intento B: Si sigue en 0, probar forzar la búsqueda en la EOA (Cuenta Principal)
            if clob_bal == 0:
                try:
                    # Cliente temporal sin proxy para ver el saldo de la EOA
                    temp_client = ClobClient(host=p_client.host, key=settings.PK, chain_id=137, signature_type=0)
                    res_eoa = temp_client.get_balance_allowance(BalanceAllowanceParams(asset_type=AssetType.COLLATERAL))
                    bal_eoa_clob = float(res_eoa.get("balance", 0)) / 10**6
                    if bal_eoa_clob > 0:
                        clob_bal = bal_eoa_clob
                        logger.info(f"[BalanceSync] Found ${bal_eoa_clob} in Main EOA Exchange Ledger")
                except:
                    pass
    except Exception as e:
        logger.error(f"[BalanceSync] Global CLOB Error: {e}")

    # ── 3. Resultado Final ──
    # Sumamos todo para no fallar
    total_usdc = clob_bal + bal_main + bal_proxy
    
    logger.info(f"[BalanceSync] TRIPLE CHECK: Total=${total_usdc:.2f} | Exchange=${clob_bal:.2f} | ProxyWallet=${bal_proxy:.2f} | MainWallet=${bal_main:.2f}")

    return {
        "bot_running": True,
        "wallet_balance_usdc": round(total_usdc, 2),
        "clob_balance": round(clob_bal, 2),
        "proxy_wallet": round(bal_proxy, 2),
        "main_wallet": round(bal_main, 2),
        "recent_trades": [] # Simplificado para diagnóstico
    }

@router.get("/logs/recent")
def get_recent_logs(lines: int = 100):
    # Mantener simple para el feed
    return {"lines": ["Diagnóstico de saldo en curso..."], "total_lines": 0}
