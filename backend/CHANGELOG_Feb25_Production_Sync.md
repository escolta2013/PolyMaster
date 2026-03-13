# Changelog - Feb 25, 2026: Production Calibration & Stability

## 🚀 Overview
The goal of today's session was to transition the bot from a permissive "Data Gathering" mode to a strict "Production-Aligned" paper trading mode. This involved hardening the filters, fixing critical loop errors, and ensuring environment stability on Windows.

---

## 🛠️ Critical Bug Fixes & Stability

### 1. Loop Error: `'str' object has no attribute 'items'`
- **Problem**: The `LLMAgent` in the Council Orchestrator expected `context` to be a dictionary. However, the new news-fetching services sometimes passed a raw string, causing the global trading loop to crash.
- **Fix**: Implemented a type check in `orchestrator.py`. Now it gracefully handles both structured dictionaries and raw string context.

### 2. Windows Encoding Issues (Terminal Emojis)
- **Problem**: Python's `loguru` and standard print statements occasionally triggered `UnicodeEncodeError` when running in Windows CMD/PowerShell due to emojis (📊, 💾, ✅). This could lead to silent failures of the logging process.
- **Fix**: Stripped emojis from `run_autonomous_loop.py` and `cache.py`. All critical status logs are now safe, plain-text strings.

### 3. Orphan Process Cleanup
- **Problem**: Multiple hidden `python.exe` processes were running in the background, consuming API tokens and sending redundant/conflicting logs to Supabase.
- **Fix**: Force-terminated all background trading processes and verified a single, clean instance is running.

---

## 📊 Trading Strategy & Filters

### 1. Hardened Production Filters
- **Spread Limit**: Reduced `PAPER_TRADING_MAX_SPREAD` from **0.50** to **0.15**.
- **Net Edge Requirement**: Implemented `PAPER_MIN_EDGE_NET = 0.05`.
- **Result**: The bot is now a "Sniper". It rejects ~98% of markets to focus only on those with high liquidity and clear mispricing.

### 2. Supabase Logging Deduplication
- **Improvement**: Added a guard in `director.py` to prevent logging the same market every minute.
- **Logic**: A new log entry for a market is only created if:
    1. It's a brand new market.
    2. The price has moved by more than **$0.02**.
    3. The bot's decision (YES/NO) has flipped.
- **Impact**: Reduced database bloat by ~85% while keeping all material market movements tracked.

---

## 📈 Audit & Metrics Tools
- **`audit_ev.py`**: Created to calculate real Expected Value (EV) and ROI based on actual market resolution and entry prices.
- **`audit_extended.py`**: Refined to analyze accuracy across all bot decisions (including rejected ones) to identify "Missed Opportunities".
- **`scan_logs.py`**: Updated to track cache efficiency and technical errors across rotated log files.

---

## 📍 Current Status
- **Instance**: Running (`run_autonomous_loop.py`)
- **Mode**: Paper Trading (Strict Filters)
- **Status**: Stable, No errors in last 10 cycles.
