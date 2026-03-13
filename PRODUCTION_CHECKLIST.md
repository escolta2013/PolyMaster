# Production Deployment Checklist & Revert Guide

The following changes were made during the "Live Simulation" phase (Feb 2026) to protect budget and enable safe testing. **These must be reviewed and/or reverted before deploying to production with real capital.**

## 1. Environment Variables (`backend/.env`)

- [ ] **`ENABLE_AUTONOMOUS_TRADING`**: verify if it should be `true` or strictly controlled/scheduled.
- [ ] **`COPY_SIMULATION`**: Change from `true` to `false` to enable REAL trading.
- [ ] **`COUNCIL_MAX_DAILY_CALLS`**: Currently at `300` for testing. Adjust based on expected volume (e.g., `1000` for highly active periods).
- [ ] **Council Cache TTLs**: Verify if the dynamic scaling (15m to 4h) in `cache.py` fits your production risk profile.
- [ ] **`GLOBAL_STOP_LOSS_PCT` & `GLOBAL_TAKE_PROFIT_PCT`**: Ensure these align with the production risk management strategy.

## 2. Code Logic (`backend/app/engines/autonomous/director.py`)

- [ ] **Rate Limiting (Cooldown)**:
    - **Current**: A hardcoded 15-minute (900s) cooldown prevents the Director from analyzing markets too frequently to save OpenAI API costs.
    - **Action**: Remove or significantly reduce this cooldown for production to ensure opportunities aren't missed. Look for the block starting with `# 1. Budget Protection: Frequency Cap`.

- [ ] **Circuit Breaker (`check_circuit_breaker`)**:
    - **Current**: Returns `True` (Green) by default because we lack a live PnL table.
    - **Action**: Implement the actual SQL query to `portfolio_snapshot` or `wallets` table to calculate real-time PnL. The method MUST return `False` if usage limits are exceeded.

## 3. Database (Supabase)

- [ ] **`council_performance` Table**:
    - **Current**: Populated with test data.
    - **Action**: Consider truncating this table or filtering by date to separate "Simulation" stats from "Production" stats.

- [ ] **Resolution Worker**:
    - **Current**: Not yet implemented/active.
    - **Action**: Ensure the worker that resolves markets and calculates Brier Scores is running reliably.

## 4. Dependencies

- [ ] **OpenRouter vs OpenAI**:
    - We switched to OpenAI direct due to rate limits on OpenRouter free tier. If switching back to OpenRouter, ensure the `orchestrator.py` logic for `reasoning_depth` is compatible.
