"""
Status Router — Dashboard API
Versión completa restaurada con búsqueda agresiva de saldo.
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

_START_TIME = datetime.now(timezone.utc)

@router.get("/status")
def get_status():
    from app.core.client import PolyClient
    from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
    from py_clob_client.client import ClobClient
    
    uptime_secs = int((datetime.now(timezone.utc) - _START_TIME).total_seconds())

    # --- BÚSQUEDA AGRESIVA DE SALDO ---
    clob_bal = 0.0
    bal_main = 0.0
    bal_proxy = 0.0
    
    try:
        # 1. Saldo On-Chain
        main_addr = Web3.to_checksum_address(Account.from_key(settings.PK).address)
        bal_main = wallet_manager.get_onchain_balance(main_addr)
        
        proxy_addr = getattr(settings, 'POLY_PROXY_ADDRESS', None)
        if proxy_addr:
            bal_proxy = wallet_manager.get_onchain_balance(Web3.to_checksum_address(proxy_addr))
            
        # 2. Saldo Exchange
        p_client = PolyClient.get_instance()
        if p_client and p_client.sdk:
            try:
                res = p_client.sdk.get_balance_allowance(BalanceAllowanceParams(asset_type=AssetType.COLLATERAL))
                clob_bal = float(res.get("balance", 0)) / 10**6
            except:
                pass
                
            if clob_bal == 0:
                try:
                    temp_client = ClobClient(host=p_client.host, key=settings.PK, chain_id=137, signature_type=0)
                    res_eoa = temp_client.get_balance_allowance(BalanceAllowanceParams(asset_type=AssetType.COLLATERAL))
                    clob_bal = float(res_eoa.get("balance", 0)) / 10**6
                except:
                    pass
    except Exception as e:
        logger.error(f"[BalanceSync] Error: {e}")

    total_usdc = clob_bal + bal_main + bal_proxy
    logger.info(f"[BalanceSync] Total=${total_usdc:.2f} | Exchange=${clob_bal:.2f} | Proxy=${bal_proxy:.2f} | Wallet=${bal_main:.2f}")

    # --- RESTO DE ESTADÍSTICAS (Versión Full) ---
    wins_total = 0
    losses_total = 0
    pnl_usdc = 0.0
    total_traded = 0.0
    recent_trades = []
    
    try:
        sb = _get_supabase()
        if sb:
            three_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
            exec_resp = sb.table("autonomous_logs").select("*").gte("detected_at", three_days_ago).order("detected_at", desc=True).limit(10).execute()
            recent_trades = exec_resp.data or []
            
            stats_resp = sb.table("copy_trades").select("usdc, outcome_value").execute()
            if stats_resp.data:
                total_traded = sum(float(r.get("usdc", 0)) for r in stats_resp.data)
                pnl_usdc = sum((float(r.get("outcome_value", 0)) - float(r.get("usdc", 0))) for r in stats_resp.data if r.get("outcome_value") is not None)
            
            wl_resp = sb.table("autonomous_logs").select("correct").in_("correct", ["WIN", "LOSS"]).execute()
            if wl_resp.data:
                wins_total = sum(1 for r in wl_resp.data if r["correct"] == "WIN")
                losses_total = sum(1 for r in wl_resp.data if r["correct"] == "LOSS")
    except Exception as e:
        logger.warning(f"Supabase stats error: {e}")

    return {
        "bot_running": True,
        "simulation_mode": settings.COPY_SIMULATION,
        "uptime_seconds": uptime_secs,
        "wallet_balance_usdc": round(total_usdc, 2),
        "wins_total": wins_total,
        "losses_total": losses_total,
        "pnl_usdc": round(pnl_usdc, 2),
        "total_traded": round(total_traded, 2),
        "recent_trades": recent_trades,
        "clob_balance": clob_bal,
        "proxy_wallet": bal_proxy
    }

@router.get("/logs/recent")
def get_recent_logs(lines: int = 100):
    log_path = "/home/ubuntu/PolyMaster/backend/logs/autonomous.log"
    if not os.path.exists(log_path): log_path = "logs/autonomous.log"
    
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            return {"lines": [l.rstrip("\n") for l in all_lines[-lines:]], "total_lines": len(all_lines)}
        except Exception as e:
            return {"lines": [f"Error: {e}"], "total_lines": 0}
    return {"lines": ["[No logs]"], "total_lines": 0}
