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
            # 72-hour rolling window instead of UTC midnight reset
            today = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()

            # Trades executed today
            exec_resp = (
                sb.table("autonomous_logs")
                .select(
                    "id, market_id, token_id, council_score, market_question, "
                    "decision, correct, detected_at, outcome, end_date_iso, "
                    "size_usdc, best_ask, best_bid, spread, source, reasoning, cache_hit"
                )
                .in_("decision", ["EXECUTED", "WOULD_EXECUTE", "EXECUTED_LIVE", "REJECTED", "FAILED", "ERROR"])
                .gte("detected_at", today)
                .order("detected_at", desc=True)
                .limit(10)
                .execute()
            )
            raw_trades = exec_resp.data or []
            
            # Enrich with copy_trades data
            for t in raw_trades:
                try:
                    ct_resp = sb.table("copy_trades").select("usdc, shares, price").eq("market_id", t["market_id"]).eq("outcome", t.get("outcome", "YES")).execute()
                    if ct_resp.data:
                        # Sum up all buys for this market/outcome combination
                        t["invested_usdc"]  = round(sum(float(r["usdc"])   for r in ct_resp.data), 4)
                        t["shares_owned"]   = round(sum(float(r["shares"]) for r in ct_resp.data), 4)
                        t["avg_entry_price"] = round(t["invested_usdc"] / t["shares_owned"], 4) if t["shares_owned"] > 0 else 0
                        t["shares_source"]  = "actual"
                    else:
                        # No copy_trades record → estimate from autonomous_logs fields
                        fallback_invested = float(t.get("size_usdc") or 0)
                        entry_price       = float(t.get("best_ask") or 0)

                        t["invested_usdc"]  = round(fallback_invested, 4)
                        t["avg_entry_price"] = round(entry_price, 4)

                        # KEY FIX: estimate shares = invested / price (Polymarket shares pay $1 at resolution)
                        if fallback_invested > 0 and entry_price > 0:
                            t["shares_owned"] = round(fallback_invested / entry_price, 4)
                            t["shares_source"] = "estimated"
                        else:
                            t["shares_owned"] = 0
                            t["shares_source"] = "unknown"

                    # ── Potential payout (each share pays $1.00 if the market resolves YES) ──
                    shares   = float(t.get("shares_owned", 0))
                    invested = float(t.get("invested_usdc", 0))
                    t["potential_payout"] = round(shares, 4)                                   # $1 per share
                    t["potential_profit"] = round(shares - invested, 4) if invested > 0 else 0
                    t["potential_roi_pct"] = round((t["potential_profit"] / invested) * 100, 1) if invested > 0 else 0

                    t["shares_source"]   = "error"

                # Use structured data if available, fallback to extraction for old records
                t["display_city"] = t.get("city")
                if not t["display_city"] or t["display_city"] == "General":
                    q = t.get("question", "").lower()
                    r = t.get("reasoning", "").lower()
                    for city_name in ["Philadelphia", "Chicago", "New York", "London", "Paris", "Madrid", "Tokyo", "Seoul", "Ankara", "Istanbul"]:
                        if city_name.lower() in q or city_name.lower() in r:
                            t["display_city"] = city_name
                            break
                    if not t["display_city"]: t["display_city"] = "General"

                t["display_type"] = t.get("market_type")
                if not t["display_type"] or t["display_type"] == "N/A":
                    q = t.get("question", "").lower()
                    if "high" in q or "above" in q: t["display_type"] = "HIGH"
                    elif "low" in q or "below" in q: t["display_type"] = "LOW"
                    elif "rain" in q: t["display_type"] = "RAIN"
                    else: t["display_type"] = "N/A"
                
                # Realized P&L for resolved trades
                if t.get("realized_pnl") is not None:
                    # Column exists and has data
                    pass
                elif t.get("correct") in ["WIN", "LOSS"]:
                    try:
                        trade_data = sb.table("copy_trades").select("usdc, outcome_value, realized_pnl").eq("market_id", t["market_id"]).execute()
                        if trade_data.data:
                            row = trade_data.data[0]
                            # Use pre-calculated P&L if available
                            if row.get("realized_pnl"):
                                t["realized_pnl"] = float(row["realized_pnl"])
                            else:
                                t["realized_pnl"] = round(float(row.get("outcome_value", 0)) - float(row.get("usdc", 0)), 2)
                    except:
                        t["realized_pnl"] = 0


            trades_today = len(raw_trades)
            recent_trades = raw_trades

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
                    .select("id, market_id, decision, correct, detected_at")
                    .in_("correct", ["WIN", "LOSS"])
                    .in_("decision", ["EXECUTED", "WOULD_EXECUTE", "EXECUTED_LIVE", "EXECUTED_SIM"])
                    .execute()
                )
                decisions = wl_resp.data or []
                # Deduplicate by market_id, keeping the one with best status (WIN > LOSS > PENDING > EXEC)
                unique_decisions = {}
                status_priority = {"WIN": 4, "LOSS": 4, "PENDING": 3, "EXECUTED_LIVE": 2, "EXECUTED_SIM": 2, "EXECUTED": 2}
                
                for d in decisions:
                    mid = d.get("market_id")
                    if not mid: continue
                    
                    current_status = d.get("correct") if d.get("correct") != "PENDING" else d.get("decision")
                    if mid not in unique_decisions:
                        unique_decisions[mid] = d
                    else:
                        existing_status = unique_decisions[mid].get("correct") if unique_decisions[mid].get("correct") != "PENDING" else unique_decisions[mid].get("decision")
                        if status_priority.get(current_status, 0) > status_priority.get(existing_status, 0):
                            unique_decisions[mid] = d
                
                for row in unique_decisions.values():
                    if row["correct"] == "WIN":
                        wins_total += 1
                    elif row["correct"] == "LOSS":
                        losses_total += 1
            except Exception:
                pass

            # Advanced Metrics from copy_trades
            total_traded = 0
            trade_count = 0
            try:
                metrics_resp = (
                    sb.table("copy_trades")
                    .select("usdc, outcome_value")
                    .execute()
                )
                rows = metrics_resp.data or []
                trade_count = len(rows)
                for row in rows:
                    usdc = float(row.get("usdc", 0))
                    ov = row.get("outcome_value")
                    total_traded += usdc
                    if ov is not None:
                        pnl_usdc += float(ov) - usdc
                
                avg_trade = total_traded / trade_count if trade_count > 0 else 0
                avg_pnl_per_trade = pnl_usdc / trade_count if trade_count > 0 else 0
            except Exception as e:
                logger.warning(f"[StatusRouter] Metrics error: {e}")
                avg_trade = 0
                avg_pnl_per_trade = 0

    except Exception as e:
        logger.warning(f"[StatusRouter] Supabase error: {e}")

    # ── Council stats from Supabase ──
    council_calls_today = 0
    cache_hits_today = 0
    markets_analyzed_today = 0
    tokens_saved_today = 0
    
    try:
        if sb:
            # LLM Calls today from logs: only count those that have a council_score (actual IA calls)
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            llm_calls = (
                sb.table("autonomous_logs")
                .select("id", count="exact")
                .gte("detected_at", today_start.isoformat())
                .not_.is_("council_score", "null")
                .execute()
            ).count or 0
            
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
            
            # This was the bug: it was counting every non-cache log as a call.
            # Now we use the strict count from line 245
            council_calls_today = llm_calls
            
            tokens_saved_today = cache_hits_today * 4000
            
            total_llm_related = llm_calls + cache_hits_today
            hit_rate_val = (cache_hits_today / total_llm_related * 100) if total_llm_related > 0 else 0
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
        "total_traded": round(total_traded, 2),
        "avg_trade_size": round(avg_trade, 2),
        "avg_pnl_trade": round(avg_pnl_per_trade, 2),
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
