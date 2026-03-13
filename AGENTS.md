# AGENTS.md — PolyMaster Operating Manual

> **READ THIS FIRST.** This is the single source of truth for understanding the PolyMaster project.
> If you are an AI agent, read this file COMPLETELY before touching any code.

---

## 🚨 CRITICAL WARNINGS

1. **This project is `polymaster/`.** There is another folder called `HolyPoly/` in the same parent directory — that is a **separate reference project** used for inspiration only. **DO NOT read, modify, or reference HolyPoly code.** If you find yourself looking at `HolyPoly/`, STOP and come back here.

2. **API keys are LIVE.** The `backend/.env` file contains real Polymarket credentials and a real OpenAI API key. Never commit this file, never log its contents, never expose it.

3. **Simulation mode is ON by default** (`COPY_SIMULATION=true`). All trades are simulated. To trade with real money, see `PRODUCTION_CHECKLIST.md`.

---

## 📋 What is PolyMaster?

PolyMaster is an **autonomous algorithmic trading platform for Polymarket** — a decentralized prediction market on Polygon where users bet on real-world events (elections, sports, crypto prices).

**What it does in simple terms:**
1. **Tracks "smart money"** — Monitors wallets of proven profitable traders ("whales") on Polymarket
2. **Detects convergence** — When ≥2 whale wallets bet on the SAME outcome of the SAME market, it triggers a "Cluster Alert"
3. **Consults an AI Council** — Sends the market to 4 specialized AI agents (via OpenAI GPT-4o) who vote on whether the bet is worth taking
4. **Executes autonomously** — If the AI Council agrees (score ≥ 0.68) AND there's enough edge (score > price + 2%), the system places a bet automatically

**Core loop (runs every 60 seconds):**
```
run_autonomous_loop.py
  → SmartMoneyTracker: Scan whale wallets for positions
  → ClusterDetector: Find markets where ≥2 whales converge
  → DirectorAgent: Evaluate clusters with Price Intelligence (ASK/BID/Spread)
      → CouncilCache: Check if this market was already analyzed
        → CACHE HIT: Reuse cached score + fresh price → decide
        → CACHE MISS: Call Council (4x OpenAI GPT-4o) → cache result → decide
  → RewardsManager (The Grinder): 🆕 Maintain orders in 'Scoring Range' to farm passive USDC
  → Log everything to Supabase (autonomous_logs table)
```

---

## 🏗️ Project Architecture

```
polymaster/
├── backend/                          # FastAPI + Python trading engines
│   ├── .env                          # ⚠️ SECRETS — Never commit
│   ├── main.py                       # FastAPI app entry point (uvicorn)
│   ├── run_autonomous_loop.py        # 🧠 THE MAIN BRAIN — Autonomous trading loop
│   ├── requirements.txt              # Python dependencies
│   ├── logs/                         # Runtime logs (autonomous.log)
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic Settings (reads .env)
│   │   │   └── logging.py            # Loguru configuration
│   │   ├── api/                      # FastAPI route definitions
│   │   ├── services/
│   │   │   ├── news_fetcher.py       # CryptoPanic news integration
│   │   │   └── telegram_bot.py       # Telegram signal notifications
│   │   └── engines/                  # ⭐ CORE TRADING ENGINES (see below)
│   │       ├── tracker/              # Phase 1: Smart Money Intelligence
│   │       ├── ghost/                # Phase 2: Statistical Arbitrage
│   │       ├── council/              # Phase 3: AI Swarm Consensus
│   │       ├── autonomous/           # Phase 5: The Director (orchestrator)
│   │       ├── wallet/               # Phase 4: Proxy Wallet Management
│   │       ├── flash/                # Phase 4: Sub-second execution
│   │       └── intelligence/         # Crypto price feeds (Binance)
│   └── SESSION_LOG_2026-02-17.md     # Detailed session log (debugging history)
│
├── frontend/                         # Next.js App Router dashboard
│   ├── .env.local                    # Frontend config (API URL)
│   ├── src/app/                      # App Router pages
│   └── src/components/               # React components
│
├── AGENTS.md                         # ⭐ THIS FILE — Read first
├── DEV_LOG.md                        # Chronological development history
├── PRODUCTION_CHECKLIST.md           # Steps to go from simulation → real trading
├── PROJECT_STATUS.md                 # Current state + what's left to do
├── implementation_plan.md            # Original roadmap (phases 0-5)
│
├── docs/reference/                   # Domain knowledge & research docs
│   ├── doc_dominio.txt               # Polymarket trading strategies overview
│   ├── doc_arquitectura.txt          # Polymarket technical infrastructure
│   └── doc_plan_maestro.txt          # Original master plan
│
└── temp_polymarket_agents/           # Reference repo (polymarket-agents fork)
```

---

## ⭐ Core Engines — Detailed Breakdown

### Engine 1: Tracker (`backend/app/engines/tracker/`)

**Purpose:** Find and grade profitable wallets ("Smart Money"), detect when they converge.

| File | Role |
|---|---|
| `tracker.py` | `SmartMoneyTracker` — Scans Polymarket Data API for wallet positions. Filters out "farmers" (market makers with YES+NO positions) to keep only directional bettors ("snipers"). |
| `indexer.py` | `PolymarketIndexer` — Indexes markets and discovers active wallets from leaderboards. |
| `grader.py` | Grades wallets into tiers: WHALE > SHARK > ORCA based on ROI, consistency, early entry. |
| `cluster_detector.py` | `ClusterDetector` — Core detection engine. Scans all smart wallets for convergence on the same market. Outputs `ClusterAlert` objects. **This is what triggers the Director.** |
| `copy_executor.py` | `CopyExecutor` — Executes trades (simulated or real). Manages daily budget, position sizing, and the CLOB SDK. |
| `worker.py` | Background worker for periodic scanning (legacy, replaced by `run_autonomous_loop.py`). |
| `router.py` | FastAPI routes for the Tracker dashboard. |

### Engine 2: Ghost (`backend/app/engines/ghost/`)

**Purpose:** Automated statistical arbitrage engine. Two strategies:
- **Hype Spikes:** Buy momentum when volume surges
- **NEH (Nothing Ever Happens):** Systematically bet NO on overpriced YES contracts
- **The Grinder (Rewards Optimization):** Passive income engine. Places BUY/SELL orders within 4.5% of midpoint on reward-eligible markets to farm daily USDC payouts.
- **Adaptive Spread:** 🆕 Execution logic that widens limit order spreads during high volatility to minimize adverse selection.

| File | Role |
|---|---|
| `liquidity.py` | Implementation of **Adaptive Spread** and market making. |
| `order_manager.py` | Low-level order submission with **Price Intelligence** (Spread/Liquidity checks). |
| `app/engines/rewards/grinder.py` | `RewardsManager` — Monitors and maintains reward-scoring orders. |
### Engine 3: Council (`backend/app/engines/council/`)

**Purpose:** AI Swarm that evaluates markets using GPT-4o. This is where OpenAI tokens are consumed.

| File | Role |
|---|---|
| `orchestrator.py` | `AgentOrchestrator` — Manages the AI council. Creates 4 `LLMAgent` instances, runs them in parallel, mediates with `RiskArbiter`, calculates final score using weighted consensus. Also computes CQI (Confidence Quality Index) and Kelly sizing. |
| `agents.py` | Legacy agent definitions. |
| `cache.py` | `CouncilCache` — **Intelligent cache with dynamic TTL.** Stores Council scores per market to prevent redundant OpenAI calls. TTL scales with market horizon (15min–4h). Invalidates when whale count changes by ≥2. Includes daily call budget (default: 300). |
| `router.py` | FastAPI routes for Council endpoints. |

**The 4 Council Agents:**
| Agent | Role | Reasoning Depth |
|---|---|---|
| `FedWatcher` | Macro-economic policy analysis, base rates | Medium |
| `RuleLawyer` | Resolution rules, UMA oracle analysis, gotchas | Medium |
| `SentimentSwarm` | Social hype, narrative cascades, crowd psychology | Low |
| `RiskArbiter` | Meta-judge, mediates conflicts, penalizes euphoria | High |

**Consensus Flow:**
```
Pass 1: FedWatcher, RuleLawyer, SentimentSwarm → analyze in parallel (3 OpenAI calls)
Pass 2: RiskArbiter mediates based on conflict regime:
  - Cohesion (σ < 0.12): 10% arbiter weight
  - Divergence (0.12 ≤ σ < 0.25): 40% arbiter weight
  - Fragmentation (σ ≥ 0.25): 60% arbiter weight
Final: weighted_score = specialist_avg × (1 - weight) + arbiter_score × weight
```

### Engine 4: Autonomous Director (`backend/app/engines/autonomous/`)

**Purpose:** The brain that connects Tracker detection → Council reasoning → Trade execution.

| File | Role |
|---|---|
| `director.py` | `DirectorAgent` — The orchestrator. Receives cluster alerts, applies temporal filters (expired markets, stale dates, ET timezone conversion), checks the CouncilCache, calls the Council if needed, calculates edge, sizes positions, and executes trades. Also includes crypto arbitrage detection (Binance price vs. Polymarket price). |
| `router.py` | FastAPI routes for enabling/disabling autonomous mode at runtime. |

**Director Decision Flow:**
```
1. Pre-filters (no OpenAI cost):
   ├── Is autonomous mode enabled?
   ├── Circuit breaker (daily budget check)
   ├── Stale ET time filter (parsed from market title)
   ├── Past date filter
   ├── Deduplication (already EXECUTED in last 12h? → skip)
   ├── Gamma API: Fetch market data, canonical ID, end_date
   ├── Strict 24h filter (skip markets ending in >24h)
   └── Price sanity (skip if price ≤0.01 or ≥0.99)

2. Council Analysis (with caching):
   ├── Check CouncilCache → HIT? Use cached score
   └── MISS? Call Council (4x GPT-4o), cache result

3. Decision modifiers:
   ├── Imminent event (<48h)? Lower threshold by 0.10
   ├── Sniping mode (<60min, >10min)? Wait
   ├── Crypto arbitrage? Override score if Binance confirms
   └── Edge validation: score - price ≥ 0.02 required

4. Execution:
   └── score ≥ threshold AND edge ≥ 0.02 → EXECUTE
```

---

## 💾 Database (Supabase)

**Project ID:** `zpdxsaacdwkswlwcafdl`

| Table | Purpose |
|---|---|
| `wallets` | Tracked smart money wallets (address, grade, is_smart_money) |
| `cluster_alerts` | Detected convergence events |
| `autonomous_logs` | Every Director decision (EXECUTED, REJECTED, SKIPPED) with council_score, reasoning, cache_hit |
| `copy_trades` | Executed trades (simulated and real) |
| `council_performance` | Individual agent predictions for backtesting accuracy |

---

## 🔧 Environment Variables (`backend/.env`)

| Variable | Purpose | Current Value |
|---|---|---|
| `OPENAI_API_KEY` | GPT-4o for Council AI | Live key |
| `AI_MODEL` | Which model to use | `gpt-4o` |
| `COUNCIL_MAX_DAILY_CALLS` | Max Council calls/day (safety budget) | `300` |
| `ENABLE_AUTONOMOUS_TRADING` | Master switch for auto-trading | `true` |
| `AUTONOMOUS_CONFIDENCE_THRESHOLD` | Minimum Council score to execute | `0.68` |
| `AUTONOMOUS_MAX_SIZE` | Max USDC per trade | `50.0` |
| `COPY_SIMULATION` | Simulate trades (no real money) | `true` |
| `COPY_MAX_PER_TRADE` | Max per individual trade | `20.0` |
| `COPY_MAX_DAILY` | Total daily budget | `200.0` |
| `GLOBAL_STOP_LOSS_PCT` | Emergency stop-loss | `0.60` (60%) |

---

## 🛠️ Development Commands

| Service | Command | URL |
|---|---|---|
| **Backend** | `cd backend && .venv\Scripts\activate && uvicorn main:app --reload` | http://127.0.0.1:8000 |
| **Frontend** | `cd frontend && npm run dev` | http://localhost:3000 |
| **Autonomous Loop** | `cd backend && .venv\Scripts\activate && python run_autonomous_loop.py` | (console output + logs) |

---

## 🎨 Coding Standards

### Backend (Python)
- **Async everywhere**: Use `async/await` for all I/O (httpx, Supabase, OpenAI)
- **Type safety**: Pydantic models for API requests/responses
- **Logging**: Use `loguru` (imported as `from app.core.logging import logger` or `from loguru import logger`)
- **Config**: Access settings via `from app.core.config import settings`
- **Engines**: Follow the modular pattern in `app/engines/`. Each engine has its own directory with `router.py` for API routes

### Frontend (Next.js)
- **Styling**: Vanilla CSS + Tailwind for layout. Use the premium dark/black aesthetic
- **Icons**: `lucide-react`
- **Data fetching**: Server Components where possible, with Suspense for loading states

---

## 📚 Documentation Map

| File | What it contains | When to read |
|---|---|---|
| `AGENTS.md` (this file) | Complete project overview | **ALWAYS READ FIRST** |
| `PROJECT_STATUS.md` | Current state, recent changes, next steps | When picking up work or planning |
| `DEV_LOG.md` | Chronological development history | When debugging or understanding past decisions |
| `PRODUCTION_CHECKLIST.md` | Steps to switch from simulation → real trading | Before deploying with real money |
| `SESSION_LOG_2026-02-17.md` | Detailed debugging session log | When troubleshooting specific bugs |
| `implementation_plan.md` | Original phase roadmap (0-5) | For historical context only |
| `docs/reference/` | Domain knowledge about Polymarket | When learning about the platform |
