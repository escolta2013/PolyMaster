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
async def get_status():
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
            if settings.PK:
                acct = Account.from_key(settings.PK)
                # This will return 100.0 if COPY_SIMULATION is True, or real balance if False
                new_bal = wallet_manager.get_onchain_balance(acct.address)
                if new_bal > 0 or not settings.COPY_SIMULATION:
                    usdc_balance = new_bal
                    _WALLET_BALANCE_CACHE["balance"] = usdc_balance
                    _WALLET_BALANCE_CACHE["last_updated"] = time.time()
        except:
            pass

    try:
        sb = _get_supabase()
        if sb:
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

            # Trades executed today
            exec_resp = (
                sb.table("autonomous_logs")
                .select("id, council_score, market_question, decision, correct, detected_at, outcome")
                .in_("decision", ["EXECUTED", "WOULD_EXECUTE"])
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

    return {
        "bot_running": True,
        "simulation_mode": settings.COPY_SIMULATION,
        "uptime_seconds": uptime_secs,
        "cycle_count": None,  # Future: expose from loop
        # Wallet & Budget
        "wallet_balance_usdc": usdc_balance,
        "trades_today": trades_today,
        "budget_spent_today": round(budget_spent, 2),
        "budget_daily_limit": settings.COPY_MAX_DAILY,
        # Performance
        "wins_total": wins_total,
        "losses_total": losses_total,
        "pnl_usdc": round(pnl_usdc, 2),
        # Council
        "council_calls_today": cache_stats.get("daily_calls", 0),
        "council_budget": settings.COUNCIL_MAX_DAILY_CALLS if hasattr(settings, "COUNCIL_MAX_DAILY_CALLS") else 300,
        "cache_hit_rate": cache_stats.get("hit_rate", "--"),
        "cached_markets": cache_stats.get("cached_markets", 0),
        "tokens_saved": cache_stats.get("tokens_saved", 0),
        "cost_saved": cache_stats.get("cost_saved", "--"),
        # Settings
        "confidence_threshold": settings.AUTONOMOUS_CONFIDENCE_THRESHOLD,
        "max_size_usdc": settings.AUTONOMOUS_MAX_SIZE,
        # Recent trades
        "recent_trades": recent_trades,
    }


@router.get("/logs/recent")
async def get_recent_logs(lines: int = 100):
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
