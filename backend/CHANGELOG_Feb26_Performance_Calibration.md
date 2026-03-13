# CHANGELOG - Feb 26: Performance Calibration & Methodology Fix

## Summary
Refinement of the performance analysis methodology and adjustment of autonomous trading filters to improve signal quality and statistical significance of paper trading data.

## Major Changes

### 1. Methodology Correction: "Definitive Resolution" Audit
- **Issue:** Previous ROI calculations used intraday price movements, inflating PnL with un-resolved gains (e.g., S&P 500 at 0.90 was counted as +100% ROI).
- **Fix:** Created `evaluate_sim_profit.py` with a strict resolution filter. 
- **Criteria:** Only markets with current price **> 0.97** (WIN) or **< 0.03** (LOSS) are included in accuracy and P&L audits.
- **Result:** Established a baseline accuracy of **54.5%** for the last 48 hours (36W - 30L), with a realized ROI of **+9.35%**.

### 2. Signal Quality Optimization
- **PAPER_MIN_EDGE_NET Adjustment:** Increased from **0.05 to 0.07**. The system now requires a 7% projected net advantage (after spread friction) to trigger a `WOULD_EXECUTE` decision.
- **eSports Exclusion:** Implemented an explicit exclusion filter for all eSports categories (Dota 2, LoL, CS2, Valorant, etc.) in `director.py`. 
- **Rationale:** Historical data showed high volatility and unreliable Council accuracy in eSports markets. Exclusion reduces noise and preserves capital for high-alpha categories (Sports/Finance).

### 3. Monitoring & Meta-Goals
- **Sample Size Target:** Set target to accumulate **150 definitively resolved markets** (currently at 66).
- **Goal:** Reach a statistically significant accuracy (Target: >58%, p < 0.05).
- **ETA for Full Audit:** March 2nd, 2026.

## Technical Details
- **Files Modified:**
    - `app/core/config.py`: Updated `PAPER_MIN_EDGE_NET`.
    - `app/engines/autonomous/director.py`: Added eSports filtering logic.
    - `evaluate_sim_profit.py`: New standalone audit script with strict resolution logic.
- **Database:** Supabase `autonomous_logs` table remains the source of truth for all simulation decisions.

---
**Status:** Calibration Phase (Strict Mode) - Bot Running.
