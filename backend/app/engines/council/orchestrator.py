from app.core.config import settings
from app.core.logging import logger
import asyncio
import re
import statistics
from typing import List, Dict, Optional
from datetime import datetime, timezone
from openai import AsyncOpenAI
from supabase import create_client, Client

class BaseAgent:
    def __init__(self, name: str, personality: str):
        self.name = name
        self.personality = personality

    async def analyze(self, market_data: Dict) -> Dict:
        raise NotImplementedError

class LLMAgent(BaseAgent):
    """
    Real AI Agent powered by OpenAI or OpenRouter.
    Uses high-fidelity personas and bias guardrails.
    """
    def __init__(self, name: str, personality: str, instructions: str, client: AsyncOpenAI, model: str, reasoning_depth: str = "medium"):
        super().__init__(name, personality)
        self.instructions = instructions
        self.client = client
        self.model = model
        self.reasoning_depth = reasoning_depth

    async def analyze(self, market_data: Dict, context: Optional[Dict] = None) -> Dict:
        if not self.client:
            return {"agent": self.name, "confidence": 0.5, "reasoning": "Agent offline (No API Key)"}

        # Handle context for Arbiter or Meta-reasoning
        context_str = ""
        if context:
            if isinstance(context, dict):
                context_str = "\n".join([f"- {k}: {v}" for k, v in context.items()])
            else:
                context_str = str(context)

        prompt = f"""
You are '{self.name}', a voting member of an elite trading council evaluating Polymarket opportunities.

Your role/personality:
{self.personality}

{self.instructions}

CRITICAL INSTRUCTION - AVOID ANCHORING BIAS:
Derive your probability estimate INDEPENDENTLY from first principles. DO NOT anchor your estimate to the 'Current YES Price'. The market price is often wrong, and your sole objective is to find the True Probability regardless of what the market currently thinks.

Your objective:
Perform a systematic 'Superforecaster' analysis.

Market Details (Current Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}):
- Question: "{market_data.get('question')}"
- End Date: {market_data.get('end_date', 'N/A')}
- Description: {str(market_data.get('description', ''))[:500]}
- Market liquidity indicator: {market_data.get('spike_magnitude', 0)}
{context_str}

Internal Thinking Process:
1. Decompose the question.
2. Gather diverse viewpoints.
3. Check historical Base Rates.
4. Weigh evidence.
5. Think probabilistically.

Output format requirements:
CRITICAL: Your response MUST end with exactly this format on the VERY LAST LINE:
Reasoning: [one summary sentence, max 15 words] | FinalConfidenceRange: X.XX-X.XX

STRICT RULES:
- NO markdown formatting (no bold, no italics).
- NO headers (#, ##, ###).
- NO numbered lists or bullet points (1., -, *).
- NO extra text after the final line.
- The output should be plain paragraphs only.

Example of CORRECT output:
The situation shows high volatility but historical precedents suggest restraint. Deterrence factors are strong.
Reasoning: High base rate for proxy conflict but low for direct strikes. | FinalConfidenceRange: 0.15-0.25

Example of WRONG output (NEVER DO THIS):
1. Break Down the Question: ...
Reasoning: ... | 0.5
        """
        max_retries = 3
        retry_delay = 5
        for attempt in range(max_retries):
            try:
                # Prepare extra parameters for reasoning models (GPT-OSS specific)
                extra_params = {}
                if "gpt-oss" in self.model:
                    extra_params = {
                        "include_reasoning": True,
                        "reasoning_depth": self.reasoning_depth
                    }

                completion = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt.strip()}],
                    max_tokens=350, # Increased for CoT
                    temperature=0.7, # Increased temperature slightly to encourage dispersion
                    extra_body=extra_params if extra_params else None
                )
                raw = completion.choices[0].message.content
                logger.info(f"Agent {self.name} raw response: {raw}")
                if "|" not in raw:
                    return {"agent": self.name, "confidence": 0.5, "reasoning": raw.strip()[:60]}
                    
                parts = raw.split("|")
                reasoning = parts[0].replace("Reasoning:", "").strip()
                
                # Robust score extraction using regex for range
                score_str = parts[1].strip()
                scores = re.findall(r"(\d*\.\d+)", score_str)
                if len(scores) >= 2:
                    confidence = (float(scores[0]) + float(scores[-1])) / 2.0
                elif len(scores) == 1:
                    confidence = float(scores[0])
                else:
                    confidence = 0.5
                
                return {
                    "agent": self.name,
                    "confidence": confidence,
                    "reasoning": reasoning
                }
            except Exception as e:
                err_msg = str(e).lower()
                err_str = str(e)

                # ── FATAL: Invalid API key — do NOT retry, do NOT return 0.5 silently ──
                # A 401 means every subsequent call will also fail. Raise immediately so
                # the orchestrator can abort the entire council session and log clearly.
                if "401" in err_str or "incorrect api key" in err_msg or "invalid api key" in err_msg:
                    logger.critical(
                        f"🔑 COUNCIL FATAL: Agent {self.name} received HTTP 401 — "
                        f"OPENAI_API_KEY is invalid or expired. "
                        f"Fix the key in backend/.env and restart. Error: {err_str[:120]}"
                    )
                    raise RuntimeError(f"Council aborted: invalid API key (401). {err_str[:80]}")

                if "rate limit" in err_msg or "429" in err_msg:
                    if attempt < max_retries - 1:
                        logger.warning(f"Agent {self.name} hit rate limit. Retrying in {retry_delay}s... (Attempt {attempt+1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                logger.error(f"Agent {self.name} failed: {e}")
                return {"agent": self.name, "confidence": 0.5, "reasoning": f"Consensus error: {str(e)[:50]}"}

class SimulationAgent(BaseAgent):
    """Fallback agent when no API keys are present."""
    async def analyze(self, market_data: Dict) -> Dict:
        await asyncio.sleep(0.5) # Simulate thinking
        score = 0.5
        if self.personality == "Conservative": score = 0.4
        elif "Aggressive" in self.personality: score = 0.8
        return {
            "agent": self.name,
            "confidence": score,
            "reasoning": f"Based on my {self.personality} analysis, I suspect a slight probability bias."
        }

class AgentOrchestrator:
    """
    Council Orchestrator: Manages the AI Swarm using standardized settings.
    """
    def __init__(self):
        # Prefer OpenRouter key if present (allows using any model), fallback to OpenAI
        if settings.OPENROUTER_API_KEY:
            api_key = settings.OPENROUTER_API_KEY
            base_url = "https://openrouter.ai/api/v1"
            logger.info("Council: Using OpenRouter as LLM backend.")
        elif settings.OPENAI_API_KEY:
            api_key = settings.OPENAI_API_KEY
            base_url = None
            logger.info("Council: Using OpenAI as LLM backend.")
        else:
            api_key = None
            base_url = None

        model = settings.AI_MODEL

        if api_key:
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            self.agents = [
                LLMAgent(
                    "FedWatcher", 
                    "Macro-economic policy expert and Superforecaster", 
                    "Core mindset:\n- Analyze markets using historical cycles and central bank policy frameworks.\n- Search for quantitative 'Base Rates' (e.g. how often has this happened before?).\n- Decompose the event into institutional incentives vs partisan noise.\n- Focus on the probability of a policy shift based on hard data.",
                    client, model, reasoning_depth="medium"
                ),
                LLMAgent(
                    "RuleLawyer", 
                    "Skeptical Polymarket rules specialist and adversarial forecaster", 
                    "Core mindset (ADVERSARIAL SKEPTIC):\n- You are the DEVIL'S ADVOCATE of this council. Your job is to find ALL the ways this trade can go WRONG.\n- Focus on resolution ambiguity (UMA or other oracles): does the wording leave room for unexpected resolution?\n- Evaluate 'Base Rates' for market FAILURES and CANCELLATIONS in this category.\n- Think like the counterparty: why would a sophisticated trader be on the other side of this bet?\n- Penalize any market with vague resolution criteria by 0.10-0.20 below your initial estimate.\n\nBias guardrails:\n- Before finalizing your score, explicitly ask yourself: 'What am I missing? What does the smart money on the other side know that I don't?'\n- Verify that the score you assign reflects genuine analytical doubt, not false confidence.\n- Never assign > 0.75 unless you have a logically airtight case with unambiguous resolution criteria.\n\nFINAL LINE MUST BE EXACTLY THIS FORMAT - NO EXCEPTIONS:\nReasoning: [maximum 15 words summarizing your SKEPTICAL conclusion] | FinalConfidenceRange: 0.XX-0.XX\n\nExample of correct output:\nReasoning: Resolution ambiguity and low base rate make this bet structurally risky. | FinalConfidenceRange: 0.30-0.45\n\nExample of WRONG output (never do this):\n1. Break Down the Question...",
                    client, model, reasoning_depth="medium"
                ),
                LLMAgent(
                    "SentimentSwarm", 
                    "Social media hype analyst", 
                    "Core mindset:\n- Track hype cycles, media amplification, and crowd reflexivity.\n- Identify viral narratives and opinion cascades.\n- Detect bubbles and overexuberance.\n\nBias guardrails:\n- Focus on perception, not truth.\n- Increase confidence if social momentum aligns with price.",
                    client, model, reasoning_depth="low"
                ),
                LLMAgent(
                    "RiskArbiter",
                    "Chief of Staff and Risk Mediator",
                    "Core mindset:\n- Act as the final judge when other agents disagree.\n- Prioritize 'Structural Confidence' and legal clarity over hype.\n- Evaluate the risk-reward ratio: is the potential win worth the uncertainty?\n- Detect 'Asymmetric' bets.\n\nBias guardrails:\n- Be skeptical of consensus when it lacks data.\n- Penalize bets if SentimentSwarm is euphoric but RuleLawyer is concerned.",
                    client, model, reasoning_depth="high"
                )
            ]
            logger.success(f"Council Armed: Ready for consensus with {model}")
        else:
            self.agents = [
                SimulationAgent("FedWatcher", "Conservative"),
                SimulationAgent("RuleLawyer", "Analytical"),
                SimulationAgent("SentimentSwarm", "Aggressive"),
                SimulationAgent("RiskArbiter", "Skeptical")
            ]
            logger.warning("Council in Simulation Mode (No LLM API Key)")
            
        self._api_key = api_key
        self._model = model
        self.consensus_threshold = settings.COUNCIL_CONSENSUS_THRESHOLD
        self.divergence_threshold = settings.COUNCIL_DIVERG_THRESHOLD # StdDev high alert
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Integration from Polymarket/agents (News & Search)
        from app.services.news_fetcher import CryptoPanicFetcher
        self.news_fetcher = CryptoPanicFetcher()

    async def validate_api_key(self) -> bool:
        """
        Sends a minimal cheap request to verify the API key works.
        Call this at startup or after config changes. Returns True if key is valid.
        Logs a CRITICAL warning if the key is invalid so the problem is immediately visible.
        """
        if not self._api_key:
            logger.warning("Council: No API key configured — running in simulation mode.")
            return False
        try:
            from openai import AsyncOpenAI
            base_url = "https://openrouter.ai/api/v1" if settings.OPENROUTER_API_KEY else None
            client = AsyncOpenAI(api_key=self._api_key, base_url=base_url)
            # Cheapest possible call: just list available models
            await client.models.list()
            logger.success(f"🔑 Council API key validated OK — model: {self._model}")
            return True
        except Exception as e:
            err = str(e)
            if "401" in err or "incorrect" in err.lower() or "invalid" in err.lower():
                logger.critical(
                    f"🔑 COUNCIL API KEY INVALID (401) — All council scores will be 0.5 (useless). "
                    f"Update OPENAI_API_KEY or OPENROUTER_API_KEY in backend/.env and restart. "
                    f"Error: {err[:150]}"
                )
            else:
                logger.error(f"Council API key validation failed: {err[:150]}")
            return False

    async def fetch_news_context(self, question: str) -> str:
        """
        Fetches context using available news services. 
        In the future, this can be expanded with Tavily or Google Search.
        """
        try:
            # 1. Check if it is a crypto market
            q_lower = question.lower()
            if any(coin in q_lower for coin in ["bitcoin", "eth", "solana", "crypto", "btc"]):
                news = await self.news_fetcher.fetch_latest_news()
                if news:
                    snippets = [f"- {n['title']} (Source: {n['source']})" for n in news[:3]]
                    return "Recent Relevant News:\n" + "\n".join(snippets)
            
            # 2. Placeholder for General News (from Polymarket/agents repo idea)
            # if os.getenv("TAVILY_API_KEY"): ...
            
            return ""
        except Exception as e:
            logger.error(f"News Context Fetch failed: {e}")
            return ""

    # ── Sportsbook Odds Helper ────────────────────────────────────────────────
    async def _fetch_sportsbook_odds(self, sport_key: str, market_question: str, polymarket_price: float = None) -> str:
        """
        Fetches live sportsbook odds from The Odds API and compares with Polymarket price.
        
        Implements the 'Sportsbook Lag' strategy: sportsbooks reprice in seconds,
        Polymarket takes 1-2 minutes. When they diverge by >5%, that gap is tradeable.
        
        Args:
            sport_key: The Odds API sport key (e.g. 'basketball_nba', 'soccer_epl')
            market_question: Full market question text for fuzzy team matching
            polymarket_price: Current Polymarket best_ask for lag calculation
            
        Returns:
            Formatted string for injection into Council prompt, or "" if unavailable.
        """
        odds_api_key = getattr(settings, 'ODDS_API_KEY', None)
        if not odds_api_key:
            return ""  # Fail-open: no key, no data, Council proceeds without it

        try:
            import httpx
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            params = {
                "apiKey": odds_api_key,
                "regions": "us,eu",           # US + EU books for consensus
                "markets": "h2h",              # Head-to-head (moneyline / winner)
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(url, params=params)
                
                if r.status_code == 401:
                    logger.warning("[ODDS_API] Invalid API key — skipping sportsbook context.")
                    return ""
                if r.status_code == 422:
                    logger.warning(f"[ODDS_API] Sport key '{sport_key}' not found or no upcoming events.")
                    return ""
                if r.status_code != 200:
                    logger.warning(f"[ODDS_API] Unexpected status {r.status_code}")
                    return ""

                remaining = r.headers.get("x-requests-remaining", "?")
                logger.debug(f"[ODDS_API] Requests remaining this month: {remaining}")

                events = r.json()
                if not events:
                    return ""

            # ── Fuzzy match: find the event relevant to this market question ──
            q_words = set(market_question.lower().split())
            best_event = None
            best_match_score = 0

            for event in events:
                home = event.get("home_team", "").lower()
                away = event.get("away_team", "").lower()
                # Score = how many words from question appear in team names
                match_score = sum(1 for w in q_words if w in home or w in away)
                if match_score > best_match_score:
                    best_match_score = match_score
                    best_event = event

            if not best_event or best_match_score < 1:
                logger.debug(f"[ODDS_API] No matching event found for: {market_question[:50]}")
                return ""

            # ── Aggregate consensus probability across all bookmakers ──
            home_team = best_event.get("home_team", "")
            away_team = best_event.get("away_team", "")
            commence = best_event.get("commence_time", "")[:10]

            home_probs, away_probs = [], []
            bookmakers_used = []

            for bk in best_event.get("bookmakers", []):
                bk_name = bk.get("title", "")
                for mkt in bk.get("markets", []):
                    if mkt.get("key") != "h2h":
                        continue
                    outcomes = {o["name"]: o["price"] for o in mkt.get("outcomes", [])}
                    h_price = outcomes.get(home_team)
                    a_price = outcomes.get(away_team)
                    if h_price and a_price:
                        # Convert decimal odds to implied probability (with vig removal)
                        total_inv = (1/h_price) + (1/a_price)
                        home_probs.append((1/h_price) / total_inv)
                        away_probs.append((1/a_price) / total_inv)
                        bookmakers_used.append(bk_name)

            if not home_probs:
                return ""

            consensus_home = sum(home_probs) / len(home_probs)
            consensus_away = sum(away_probs) / len(away_probs)
            n_books = len(bookmakers_used)

            # ── Lag detection: compare sportsbook consensus vs Polymarket ──────
            lag_str = ""
            if polymarket_price is not None:
                # Determine which team Polymarket is pricing (YES side)
                # Heuristic: if question mentions home team → compare with consensus_home
                q_lower_check = market_question.lower()
                home_words = set(home_team.lower().split())
                home_mention = any(w in q_lower_check for w in home_words if len(w) > 3)

                sportsbook_prob = consensus_home if home_mention else consensus_away
                lag = sportsbook_prob - polymarket_price

                if abs(lag) >= 0.05:
                    direction = "SPORTSBOOK > POLYMARKET" if lag > 0 else "POLYMARKET > SPORTSBOOK"
                    lag_str = (
                        f"  ⚡ LAG SIGNAL DETECTED: Sportsbook={sportsbook_prob:.3f} vs "
                        f"Polymarket={polymarket_price:.3f} | Gap={abs(lag):.3f} ({direction})"
                    )
                    logger.warning(f"[ODDS_API] {lag_str.strip()}")
                else:
                    lag_str = f"  Prices aligned: Sportsbook={sportsbook_prob:.3f} ≈ Polymarket={polymarket_price:.3f} (gap={abs(lag):.3f})"

            lines = [
                f"[STRUCTURED DATA - Sportsbook Consensus ({n_books} books, {sport_key})]",
                f"  Event: {away_team} @ {home_team} ({commence})",
                f"  Consensus: {home_team}={consensus_home:.3f} | {away_team}={consensus_away:.3f}",
            ]
            if lag_str:
                lines.append(lag_str)

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"[ODDS_API] Exception fetching odds for {sport_key}: {e}")
            return ""  # Always fail-open

    async def fetch_structured_context(self, question: str, market_price: float = None) -> str:
        """
        Injects structured real-world data into Council context based on market category.
        - NBA: SUSPENDED — excluded from system (EV=-0.162, n=234, 2026-03-10)
        - NFL: Sportsbook odds (The Odds API)
        - Soccer (EPL/LaLiga/UCL): Sportsbook odds (The Odds API)
        - Tennis: SUSPENDED — excluded from system (EV=-0.269, n=75, 2026-03-10)
        - Fed/FOMC/Inflation: Hardcoded latest macro data (updated periodically)
        - Weather: Historical base rates
        """
        q_lower = question.lower()
        context_lines = []

        # ── GUARD: NBA and Tennis are excluded from the system ────────────────
        # Director early-exits these categories before calling the Council,
        # so this code should never be reached. Guard added for safety.
        # Reactivate by removing these checks when edge is re-established.
        _nba_guard = any(k in q_lower for k in [
            "nba", "celtics", "lakers", "warriors", "knicks", "nets", "bucks",
            "heat", "nuggets", "suns", "clippers", "grizzlies", "thunder",
            "mavs", "spurs", "rockets", "pistons", "pacers", "hawks", "hornets",
            "wizards", "magic", "raptors", "cavaliers", "timberwolves", "jazz",
            "pelicans", "kings", "blazers",
        ])
        _tennis_guard = any(k in q_lower for k in [
            "tennis", " atp ", "wta ", "wimbledon", "roland garros", "djokovic",
            "alcaraz", "sinner", "medvedev", "swiatek", "sabalenka",
            "bnp paribas open", "dubai tennis", "indian wells", "miami open",
        ])
        if _nba_guard or _tennis_guard:
            category = "NBA" if _nba_guard else "Tennis"
            logger.warning(
                f"[STRUCTURED_DATA] {category} market reached orchestrator despite director guard. "
                f"Returning empty context — category is suspended."
            )
            return ""
        # ─────────────────────────────────────────────────────────────────────

        # ── NBA / Basketball ─────────────────────────────────────────────────
        is_nba = any(k in q_lower for k in [
            "nba", "basketball", "spread", "over/under", "o/u", "points",
            "clippers", "grizzlies", "warriors", "thunder", "bulls", "knicks",
            "nets", "bucks", "heat", "mavs", "celtics", "lakers", "nuggets",
            "suns", "spurs", "rockets", "pistons", "pacers", "hawks", "hornets",
            "wizards", "magic", "raptors", "cavaliers", "timberwolves", "jazz",
            "pelicans", "kings", "blazers", "okc"
        ])
        if is_nba:
            # 1. balldontlie.io — recent game scores for context
            try:
                import httpx
                from datetime import timedelta
                headers = {"Authorization": settings.BALLDONTLIE_API_KEY} if settings.BALLDONTLIE_API_KEY else {}
                today = datetime.now(timezone.utc)
                start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
                end_date = today.strftime("%Y-%m-%d")

                async with httpx.AsyncClient(timeout=5.0) as client:
                    params = {"start_date": start_date, "end_date": end_date, "per_page": 10}
                    r = await client.get("https://api.balldontlie.io/v1/games", params=params, headers=headers)
                    if r.status_code == 200:
                        nba_data = r.json().get("data", [])
                        if nba_data:
                            context_lines.append("[STRUCTURED DATA - NBA Recent Games]")
                            for g in nba_data[:3]:
                                ht = g.get("home_team", {}).get("abbreviation", "")
                                vt = g.get("visitor_team", {}).get("abbreviation", "")
                                hs = g.get("home_team_score", 0)
                                vs = g.get("visitor_team_score", 0)
                                status = g.get("status", "")
                                date_str = g.get("date", "")
                                season = g.get("season", 0)
                                # Safety: only include games from 2026 or later to avoid historical confusion
                                if season < 2026 and "2026" not in date_str:
                                    continue
                                    
                                context_lines.append(f"  {vt} @ {ht}: {vs}-{hs} ({status})")
                        logger.info("Council: Injected NBA scores from balldontlie.io.")
                    else:
                        logger.warning(f"[STRUCTURED_DATA] NBA fetch FAILED: {r.status_code}")
            except Exception as e:
                logger.error(f"[STRUCTURED_DATA] NBA fetch Exception: {e}")

            # 2. The Odds API — sportsbook consensus + lag detection
            odds_ctx = await self._fetch_sportsbook_odds("basketball_nba", question, market_price)
            if odds_ctx:
                context_lines.append(odds_ctx)
                logger.info("Council: Injected NBA sportsbook odds + lag signal.")

        # ── NFL / American Football ───────────────────────────────────────────
        is_nfl = any(k in q_lower for k in [
            "nfl", "super bowl", "touchdown", "quarterback", "chiefs", "eagles",
            "cowboys", "patriots", "bills", "ravens", "49ers", "packers",
            "bears", "giants", "jets", "dolphins", "broncos", "raiders",
            "chargers", "colts", "texans", "titans", "jaguars", "bengals",
            "browns", "steelers", "lions", "vikings", "falcons", "saints",
            "buccaneers", "panthers", "cardinals", "rams", "seahawks"
        ])
        if is_nfl:
            odds_ctx = await self._fetch_sportsbook_odds("americanfootball_nfl", question, market_price)
            if odds_ctx:
                context_lines.append(odds_ctx)
                logger.info("Council: Injected NFL sportsbook odds + lag signal.")

        # ── Soccer / Football ─────────────────────────────────────────────────
        is_soccer = any(k in q_lower for k in [
            "premier league", "epl", "la liga", "serie a", "bundesliga",
            "ligue 1", "champions league", "ucl", "europa league", "fa cup",
            "manchester", "arsenal", "chelsea", "liverpool", "tottenham",
            "barcelona", "real madrid", "atletico", "juventus", "milan",
            "inter", "psg", "bayern", "dortmund", "both teams to score", "btts",
            "clean sheet", "match winner", "first goalscorer"
        ])
        if is_soccer:
            # Try EPL first, then Champions League, then La Liga
            soccer_keys = ["soccer_epl", "soccer_uefa_champs_league", "soccer_spain_la_liga",
                          "soccer_italy_serie_a", "soccer_germany_bundesliga", "soccer_france_ligue_one"]
            for sk in soccer_keys:
                odds_ctx = await self._fetch_sportsbook_odds(sk, question, market_price)
                if odds_ctx:
                    context_lines.append(odds_ctx)
                    logger.info(f"Council: Injected soccer sportsbook odds ({sk}) + lag signal.")
                    break  # Stop at first match

        # ── Tennis ────────────────────────────────────────────────────────────
        is_tennis = any(k in q_lower for k in [
            "tennis", "atp", "wta", "grand slam", "wimbledon", "us open",
            "french open", "australian open", "roland garros", "djokovic",
            "alcaraz", "sinner", "medvedev", "rublev", "swiatek", "sabalenka",
            "set winner", "match winner", "straight sets"
        ])
        if is_tennis:
            for tk in ["tennis_atp_french_open", "tennis_atp_us_open",
                       "tennis_atp_wimbledon", "tennis_atp_australian_open",
                       "tennis_atp", "tennis_wta"]:
                odds_ctx = await self._fetch_sportsbook_odds(tk, question, market_price)
                if odds_ctx:
                    context_lines.append(odds_ctx)
                    logger.info(f"Council: Injected tennis sportsbook odds ({tk}) + lag signal.")
                    break

        # ── Fed / FOMC / Inflation ────────────────────────────────────────────
        is_fed = any(k in q_lower for k in [
            "fed", "fomc", "inflation", "cpi", "rate cut", "rate hike",
            "interest rate", "jerome powell", "federal reserve"
        ])
        if is_fed:
            context_lines.append("[STRUCTURED DATA - Latest Macro Context (as of Mar 2026)]")
            context_lines.append("  US CPI (Feb 2026): +2.8% YoY (above 2% target)")
            context_lines.append("  Fed Funds Rate: 4.25%-4.50% (held at Jan 2026 FOMC meeting)")
            context_lines.append("  Last FOMC Statement: 'No rate cuts expected until inflation sustainably reaches 2%'")
            context_lines.append("  Market Implied Rate Cuts (CME FedWatch): ~1-2 cuts priced for H2 2026")
            logger.info("Council: Injected Fed/FOMC structured context.")

        # ── Weather ───────────────────────────────────────────────────────────
        is_weather = any(k in q_lower for k in [
            "temperature", "degrees", "seoul", "celsius", "fahrenheit", "weather"
        ])
        if is_weather:
            context_lines.append("[STRUCTURED DATA - Weather Context]")
            context_lines.append("  Note: Seoul Mar avg high: 10°C (50°F). Significant variation is unusual mid-month.")
            context_lines.append("  Tip: Historical base rate for extreme temperature days in March: ~15%.")
            logger.info("Council: Injected Weather structured context.")

        return "\n".join(context_lines) if context_lines else ""

    async def get_market_consensus(self, market_data: Dict) -> Dict:
        """
        Deliberative Council with Conflict Arbitration (Quant-Grade).
        Pass 1: Specialists analyze.
        Pass 2: Risk Arbiter mediates based on tiers.
        Raises RuntimeError if the API key is invalid (401) so the Director can log
        FAILED instead of silently storing a worthless 0.5 score.
        """
        logger.info(f"Initiating High-Fidelity Consensus for: {market_data.get('question')[:50]}...")
        
        # 0. Context Enhancement (News + Structured Real-World Data)
        question_str = market_data.get('question', '')
        news_context = await self.fetch_news_context(question_str)
        market_price_for_odds = float(market_data.get('best_ask') or market_data.get('price') or 0.5)
        structured_context = await self.fetch_structured_context(question_str, market_price=market_price_for_odds)
        combined_context = "\n".join(filter(None, [news_context, structured_context]))
        if combined_context:
            logger.info("Council: Enhanced reasoning with live news + structured data context.")
            if not market_data.get('context'):
                market_data['enhanced_context'] = combined_context
            else:
                market_data['enhanced_context'] = f"{market_data['context']}\n{combined_context}"

        # 1. Specialist Pass (Parallel)
        # NOTE: If any agent raises RuntimeError (e.g., 401 invalid key), it propagates
        # up to the caller (Director) which logs FAILED and skips caching the bad score.
        specialist_agents = [a for a in self.agents if a.name != "RiskArbiter"]
        tasks = [agent.analyze(market_data, context=market_data.get('enhanced_context')) for agent in specialist_agents]
        specialist_results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Extract Specialist Metrics
        confidences = [r['confidence'] for r in specialist_results]
        avg_confidence = sum(confidences) / len(specialist_results)
        std_dev = statistics.stdev(confidences) if len(confidences) > 1 else 0.0
        
        # 2. Risk Arbiter Pass (Mediation)
        arbiter_agent = next((a for a in self.agents if a.name == "RiskArbiter"), None)
        final_score = avg_confidence
        regime = "Cohesion"
        arbiter_result = {"reasoning": "N/A", "confidence": avg_confidence}

        if arbiter_agent:
            # Classification of Conflict (User's Tiers)
            if std_dev < 0.12:
                regime = "Cohesion"
                arbiter_weight = 0.1 # Minimal smoothing
            elif 0.12 <= std_dev < 0.25:
                regime = "Divergence"
                arbiter_weight = 0.4 # Moderated balance
            else:
                regime = "Fragmentation"
                arbiter_weight = 0.6 # Arbiter control
            
            # Prepare Arbiter Context
            expert_scores = {r['agent']: r['confidence'] for r in specialist_results}
            arbiter_context = {
                "FedScore": expert_scores.get("FedWatcher"),
                "RuleScore": expert_scores.get("RuleLawyer"),
                "SentScore": expert_scores.get("SentimentSwarm"),
                "SpecialistAvg": round(avg_confidence, 3),
                "Dispersion": round(std_dev, 3),
                "ConflictRegime": regime
            }
            
            arbiter_result = await arbiter_agent.analyze(market_data, context=arbiter_context)
            
            # Weighted Strategy calculation
            final_score = (avg_confidence * (1 - arbiter_weight)) + (arbiter_result['confidence'] * arbiter_weight)
        
        # SAFETY: Clamp final_score to valid probability range [0.0, 1.0]
        final_score = max(0.0, min(1.0, final_score))
        
        # Log warning if clamping occurred (indicates upstream bug)
        if final_score != ((avg_confidence * (1 - arbiter_weight)) + (arbiter_result['confidence'] * arbiter_weight) if arbiter_agent else avg_confidence):
            logger.warning(f"Council: final_score was clamped to {final_score} (original calculation exceeded [0,1] range)")
            
        logger.info(f"Council Scores: [FedWatcher: {expert_scores.get('FedWatcher', 0):.3f}] [RuleLawyer: {expert_scores.get('RuleLawyer', 0):.3f}] [SentimentSwarm: {expert_scores.get('SentimentSwarm', 0):.3f}] [RiskArbiter: {arbiter_result['confidence']:.3f}]")
        logger.info(f"Council Final Weighted Score (by RiskArbiter): {final_score:.3f}")

        # 3. Quant Metric: Confidence Quality Index (CQI)
        # CQI = (1 - Dispersion) * |SpecialistAvg - Price|
        try:
            current_price = float(market_data.get('price'))
        except (ValueError, TypeError, Exception):
            current_price = 0.5 # Fallback if 'N/A', None, or error

        distance_from_price = abs(avg_confidence - current_price)
        cqi = (1 - std_dev) * distance_from_price
        
        # Additional Metadata for DB
        majority_dir = "YES" if avg_confidence > 0.5 else "NO"
        minority_agent = specialist_results[0]['agent'] # Placeholder for logic if needed
        # Find agent furthest from mean
        raw_diffs = {r['agent']: abs(r['confidence'] - avg_confidence) for r in specialist_results}
        outlier_agent = max(raw_diffs, key=raw_diffs.get)

        # Execution Rule: FinalScore > threshold (or < 1-threshold for NO) AND CQI > Threshold
        cqi_threshold = settings.COUNCIL_CQI_THRESHOLD # Adjusted from 0.1 for initial sensitivity
        
        signal_side = "YES" if final_score >= self.consensus_threshold else ("NO" if final_score <= (1 - self.consensus_threshold) else "NONE")
        is_consensus = signal_side != "NONE" and cqi > cqi_threshold
        
        # 4. Sizing Layer: Fractional Kelly Criterion
        # Kelly % = (p - price) / (1 - price) if p > price
        # We use a conservative Fractional Kelly (e.g., 0.10) to mitigate model risk.
        kelly_size_raw = 0.0
        if is_consensus:
            if final_score > current_price:
                # Long (YES)
                kelly_size_raw = (final_score - current_price) / (1 - current_price)
            elif final_score < current_price:
                # Short (NO)
                kelly_size_raw = (current_price - final_score) / current_price
            
            # Application of Fractional Kelly and CQI dampening
            # More divergence = smaller size. Better CQI = more confidence.
            fraction = settings.COUNCIL_KELLY_FRACTION # Base X% Kelly
            suggested_allocation_pct = kelly_size_raw * fraction * (1 - std_dev)
        else:
            suggested_allocation_pct = 0.0

        # Alarms: LogLoss Tail Risk Detector (Virtual)
        # If final_score is extreme (e.g. >0.90) but Price is <0.40, we trigger a tail risk warning.
        is_tail_risk = (final_score > 0.90 and current_price < 0.40) or (final_score < 0.10 and current_price > 0.60)

        # 5. Persistence: Save to Supabase (Council Performance)
        try:
            db_entries = []
            
            # Specialist entries
            for r in specialist_results:
                db_entries.append({
                    "market_id": market_data.get('id'),
                    "market_question": market_data.get('question'),
                    "agent_name": r['agent'],
                    "prediction_score": r['confidence'],
                    "market_price_at_prediction": current_price,
                    "regime": regime,
                    "status": "pending"
                })
            
            # Arbiter entry
            if arbiter_result and arbiter_result.get('agent') == "RiskArbiter":
                db_entries.append({
                    "market_id": market_data.get('id'),
                    "market_question": market_data.get('question'),
                    "agent_name": "RiskArbiter",
                    "prediction_score": arbiter_result['confidence'],
                    "market_price_at_prediction": current_price,
                    "regime": regime,
                    "status": "pending"
                })

            # Final Council Consensus entry
            db_entries.append({
                "market_id": market_data.get('id'),
                "market_question": market_data.get('question'),
                "agent_name": "Council",
                "prediction_score": final_score,
                "market_price_at_prediction": current_price,
                "cqi": cqi,
                "regime": regime,
                "status": "pending"
            })
            
            self.supabase.table("council_performance").insert(db_entries).execute()
            logger.debug(f"Persistence: Saved {len(db_entries)} entries for market {market_data.get('id')}")
        except Exception as e:
            logger.error(f"Persistence Error: Failed to save council metrics: {e}")

        try:
            spike_mag = float(market_data.get('spike_magnitude', 0))
        except:
            spike_mag = 0.0

        return {
            "market_id": market_data.get('id'),
            "consensus_reached": is_consensus,
            "signal_side": signal_side,
            "regime": regime,
            "final_score": round(final_score, 3),
            "cqi": round(cqi, 3),
            "suggested_sizing": {
                "kelly_raw": round(kelly_size_raw, 4),
                "allocation_pct": round(max(0, suggested_allocation_pct), 4),
                "potential_alpha": round(final_score - current_price, 3) if signal_side == "YES" else round(current_price - final_score, 3)
            },
            "metrics": {
                "specialist_avg": round(avg_confidence, 2),
                "dispersion": round(std_dev, 3),
                "market_price": current_price,
                "distance_from_price": round(distance_from_price, 3),
                "outlier_agent": outlier_agent,
                "majority_direction": majority_dir,
                "spike_regime": "High" if spike_mag > 2.0 else "Normal",
                "tail_risk_alert": is_tail_risk
            },
            "arbiter_report": arbiter_result,
            "agent_reports": specialist_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }