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

# ── Bot start time (tracks uptime from when this module was first loaded) ──
_START_TIME = datetime.now(timezone.utc)
_WALLET_BALANCE_CACHE = {"balance": 0.0, "last_updated": 0}

@router.get("/status")
def get_status():
    """
    Returns a JSON snapshot of the bot's current state.
    Called every 5 seconds by the dashboard.
    """
    from app.core.config import settings
    from app.engines.council.cache import council_cache

    uptime_secs = int((datetime.now(timezone.utc) - _START_TIME).total_seconds())

    # ── Council cache stats ──
    cache_stats = council_cache.get_stats()

    # ── Supabase queries ──
    trades_today = 0
    budget_spent = 0.0
    wins_total = 0
    losses_total = 0
    pnl_usdc = 0.0
    recent_trades = []

    # ── Poly USDC Balance (Cached 60s) ──
    usdc_balance = _WALLET_BALANCE_CACHE["balance"]
    if time.time() - _WALLET_BALANCE_CACHE["last_updated"] > 60:
        try:
            from app.core.client import PolyClient
            from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
            
            p_client = PolyClient.get_instance()
            clob_bal = 0.0
            
            # Step 1: Try Internal CLOB Balance (The funds ready to trade)
            try:
                if p_client and p_client.sdk:
                    clob_bal_raw = p_client.sdk.get_balance_allowance(BalanceAllowanceParams(asset_type=AssetType.COLLATERAL))
                    clob_bal = float(clob_bal_raw.get("balance", 0)) / 10**6
                    logger.debug(f"[StatusRouter] Internal CLOB Balance: ${clob_bal}")
            except Exception as ce:
                logger.warning(f"[StatusRouter] CLOB balance fetch failed: {ce}")

            # Step 2: Try On-Chain Balance (Funds in wallet, not yet deposited)
            chain_bal = 0.0
            try:
                target_address = settings.POLY_PROXY_ADDRESS if hasattr(settings, 'POLY_PROXY_ADDRESS') and settings.POLY_PROXY_ADDRESS else Account.from_key(settings.PK).address
                chain_bal = wallet_manager.get_onchain_balance(target_address)
                logger.debug(f"[StatusRouter] On-Chain Balance: ${chain_bal}")
            except Exception as we:
                logger.warning(f"[StatusRouter] On-chain balance fetch failed: {we}")

            # Prioritize CLOB balance for the trading dashboard
            final_bal = clob_bal if clob_bal > 0 else chain_bal
            
            # Always respect COPY_SIMULATION if it returns a fake balance (100.0)
            if settings.COPY_SIMULATION and chain_bal == 100.0:
                final_bal = 100.0

            usdc_balance = final_bal
            _WALLET_BALANCE_CACHE["balance"] = usdc_balance
            _WALLET_BALANCE_CACHE["last_updated"] = time.time()
            
        except Exception as e:
            logger.error(f"[StatusRouter] Critical balance update error: {e}")

    try:
        sb = _get_supabase()
        if sb:
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

            # Trades executed today
            exec_resp = (
                sb.table("autonomous_logs")
                .select("id, council_score, market_question, decision, correct, detected_at, outcome")
                .in_("decision", ["EXECUTED", "WOULD_EXECUTE", "EXECUTED_LIVE", "REJECTED", "FAILED", "ERROR"])
                .gte("detected_at", today)
                .order("detected_at", desc=True)
                .limit(8)
                .execute()
            )
            today_trades = exec_resp.data or []
            trades_today = len(today_trades)
            recent_trades = today_trades

            # Spend from copy_trades (real or simulated executions)
            try:
                spend_resp = (
                    sb.table("copy_trades")
                    .select("usdc")
                    .gte("timestamp", today)
                    .execute()
                )
                budget_spent = sum(r.get("usdc", 0) for r in (spend_resp.data or []))
            except Exception:
                pass

            # Win / Loss totals (all time)
            try:
                wl_resp = (
                    sb.table("autonomous_logs")
                    .select("correct")
                    .in_("correct", ["WIN", "LOSS"])
                    .in_("decision", ["EXECUTED", "WOULD_EXECUTE"])
                    .execute()
                )
                for row in (wl_resp.data or []):
                    if row["correct"] == "WIN":
                        wins_total += 1
                    elif row["correct"] == "LOSS":
                        losses_total += 1
            except Exception:
                pass

            # Simulated P&L from copy_trades
            try:
                pnl_resp = (
                    sb.table("copy_trades")
                    .select("usdc, outcome_value")
                    .execute()
                )
                for row in (pnl_resp.data or []):
                    ov = row.get("outcome_value")
                    usdc = row.get("usdc", 0)
                    if ov is not None:
                        pnl_usdc += float(ov) - float(usdc)
            except Exception:
                pass

    except Exception as e:
        logger.warning(f"[StatusRouter] Supabase error: {e}")

    # ── Council stats from Supabase ──
    council_calls_today = 0
    cache_hits_today = 0
    markets_analyzed_today = 0
    tokens_saved_today = 0
    
    try:
        if sb:
            # Stats for the last 24h
            stats_resp = (
                sb.table("autonomous_logs")
                .select("cache_hit, market_id")
                .gte("detected_at", today)
                .execute()
            )
            stats_data = stats_resp.data or []
            
            markets_analyzed_today = len(set(r.get("market_id") for r in stats_data))
            cache_hits_today = sum(1 for r in stats_data if r.get("cache_hit") is True)
            council_calls_today = sum(1 for r in stats_data if r.get("cache_hit") is False)
            tokens_saved_today = cache_hits_today * 4000
            
            total_checks = len(stats_data)
            hit_rate_val = (cache_hits_today / total_checks * 100) if total_checks > 0 else 0
            cache_hit_rate_str = f"{hit_rate_val:.1f}%"
    except Exception as e:
        logger.warning(f"[StatusRouter] Council stats error: {e}")
        cache_hit_rate_str = "--"

    return {
        "bot_running": True,
        "simulation_mode": settings.COPY_SIMULATION,
        "uptime_seconds": uptime_secs,
        "cycle_count": None,
        # Wallet & Budget
        "wallet_balance_usdc": usdc_balance,
        "trades_today": trades_today,
        "budget_spent_today": round(budget_spent, 2),
        "budget_daily_limit": settings.COPY_MAX_DAILY,
        # Performance
        "wins_total": wins_total,
        "losses_total": losses_total,
        "pnl_usdc": round(pnl_usdc, 2),
        # Council (Unified from DB)
        "council_calls_today": council_calls_today,
        "council_budget": settings.COUNCIL_MAX_DAILY_CALLS if hasattr(settings, "COUNCIL_MAX_DAILY_CALLS") else 300,
        "cache_hit_rate": cache_hit_rate_str,
        "cached_markets": markets_analyzed_today,
        "tokens_saved": f"~{tokens_saved_today:,}",
        "cost_saved": f"~${(tokens_saved_today / 1000 * 0.005):.2f}",
        # Settings
        "confidence_threshold": settings.AUTONOMOUS_CONFIDENCE_THRESHOLD,
        "max_size_usdc": settings.AUTONOMOUS_MAX_SIZE,
        # Recent trades
        "recent_trades": recent_trades,
    }


@router.get("/logs/recent")
def get_recent_logs(lines: int = 100):
    """
    Returns the last N lines of the autonomous.log file.
    The dashboard streams this to its live log panel.
    """
    log_paths = [
        "logs/autonomous.log",
        "../logs/autonomous.log",
    ]

    for path in log_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
                recent = [l.rstrip("\n") for l in all_lines[-lines:]]
                return {"lines": recent, "total_lines": len(all_lines)}
            except Exception as e:
                logger.warning(f"[StatusRouter] Could not read log {path}: {e}")

    return {"lines": ["[No log file found]"], "total_lines": 0}
