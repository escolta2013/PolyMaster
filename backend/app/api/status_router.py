"""
Status Router — Dashboard API
Provides real-time bot status, recent trades, and log streaming
for the terminal dashboard (GET /dashboard).
"""

import os
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter
from loguru import logger

router = APIRouter(prefix="/api", tags=["status"])


def _get_supabase():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)


import time
from eth_account import Account
from app.engines.wallet.manager import wallet_manager   
from app.core.config import settings

# ── Bot start time (tracks uptime from when this module was first loaded) ──
_START_TIME = datetime.now(timezone.utc)
_WALLET_BALANCE_CACHE = {"balance": 0.0, "last_updated": 0}

@router.get("/status")
def get_status():
    """
    Returns a JSON snapshot of the bot's current state. 
    Called every 5 seconds by the dashboard.
    """
    from app.engines.council.cache import council_cache 
    from app.core.client import PolyClient
    from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
    from web3 import Web3

    uptime_secs = int((datetime.now(timezone.utc) - _START_TIME).total_seconds())

    # ── Council cache stats ──
    cache_stats = council_cache.get_stats()

    # --- Initialize all variables first ---
    wins_total = 0
    losses_total = 0
    pnl_usdc = 0.0
    total_traded = 0.0
    avg_trade = 0.0
    avg_pnl_per_trade = 0.0
    trades_today = 0
    budget_spent = 0.0
    recent_trades = []
    
    # ── Poly USDC Balance (Exhaustive Sync) ──
    clob_bal = 0.0
    bal_main = 0.0
    bal_proxy = 0.0
    
    try:
        p_client = PolyClient.get_instance()
        # 1. Check CLOB (Exchange Ledger)
        if p_client and p_client.sdk:
            try:
                clob_bal_raw = p_client.sdk.get_balance_allowance(BalanceAllowanceParams(asset_type=AssetType.COLLATERAL))
                clob_bal = float(clob_bal_raw.get("balance", 0)) / 10**6
            except Exception as e:
                logger.debug(f"CLOB balance fetch error: {e}")

        # 2. Check On-Chain (Wallets)
        main_addr = Account.from_key(settings.PK).address
        bal_main = wallet_manager.get_onchain_balance(main_addr)

        proxy_addr = getattr(settings, 'POLY_PROXY_ADDRESS', None)
        if proxy_addr:
            bal_proxy = wallet_manager.get_onchain_balance(Web3.to_checksum_address(proxy_addr))

    except Exception as e:
        logger.error(f"[StatusRouter] Balance fetch error: {e}")

    # Aggregated Balance (Summing all sources to ensure we see the $11.00)
    usdc_balance = clob_bal + bal_main + bal_proxy
    
    # Diagnostic logging for the dashboard console
    logger.info(f"[BalanceSync] Total: ${usdc_balance:.2f} | Exchange: ${clob_bal:.2f} | Proxy: ${bal_proxy:.2f} | Wallet: ${bal_main:.2f}")

    # --- Supabase Statistics ---
    try:
        sb = _get_supabase()
        if sb:
            today = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
            exec_resp = (
                sb.table("autonomous_logs")
                .select("*")
                .in_("decision", ["EXECUTED", "WOULD_EXECUTE", "EXECUTED_LIVE", "REJECTED", "FAILED", "ERROR"]) 
                .gte("detected_at", today)
                .order("detected_at", desc=True)
                .limit(10)
                .execute()
            )
            recent_trades = exec_resp.data or []
            trades_today = len(recent_trades)

            # Performance stats
            stats_resp = sb.table("copy_trades").select("usdc, outcome_value").execute()
            if stats_resp.data:
                rows = stats_resp.data
                total_traded = sum(float(r.get("usdc", 0)) for r in rows)
                pnl_usdc = sum((float(r.get("outcome_value", 0)) - float(r.get("usdc", 0))) for r in rows if r.get("outcome_value") is not None)
                avg_trade = total_traded / len(rows) if len(rows) > 0 else 0
                avg_pnl_per_trade = pnl_usdc / len(rows) if len(rows) > 0 else 0

            # Win/Loss counts
            wl_resp = sb.table("autonomous_logs").select("correct").in_("correct", ["WIN", "LOSS"]).execute()
            if wl_resp.data:
                wins_total = sum(1 for r in wl_resp.data if r["correct"] == "WIN")
                losses_total = sum(1 for r in wl_resp.data if r["correct"] == "LOSS")

    except Exception as e:
        logger.warning(f"[StatusRouter] Supabase error: {e}")

    return {
        "bot_running": True,
        "simulation_mode": settings.COPY_SIMULATION,    
        "uptime_seconds": uptime_secs,
        "wallet_balance_usdc": round(usdc_balance, 2),
        "trades_today": trades_today,
        "budget_spent_today": round(budget_spent, 2),   
        "budget_daily_limit": settings.COPY_MAX_DAILY,  
        "wins_total": wins_total,
        "losses_total": losses_total,
        "pnl_usdc": round(pnl_usdc, 2),
        "total_traded": round(total_traded, 2),
        "avg_trade_size": round(avg_trade, 2),
        "avg_pnl_trade": round(avg_pnl_per_trade, 2),   
        "recent_trades": recent_trades,
    }


@router.get("/logs/recent")
def get_recent_logs(lines: int = 100):
    log_path = "/home/ubuntu/PolyMaster/backend/logs/autonomous.log"
    if not os.path.exists(log_path):
        log_path = "logs/autonomous.log"

    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            recent = [l.rstrip("\n") for l in all_lines[-lines:]]
            return {"lines": recent, "total_lines": len(all_lines)}
        except Exception as e:
            return {"lines": [f"Error reading log: {e}"], "total_lines": 0}

    return {"lines": ["[No log file found]"], "total_lines": 0}
