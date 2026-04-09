"""
Council Analysis Cache — Dynamic TTL based on market horizon.

Core idea:
- The Council's probability score (0.00-1.00) for a market question rarely changes
  in the short term. What changes is the PRICE, which is free to fetch.
- We cache the score and re-evaluate the DECISION (execute vs reject) locally
  using: cached_score + fresh_price → edge calculation → decision.
- This eliminates 90%+ of redundant OpenAI calls.

Dynamic TTL Strategy:
  > 12h to resolution  →  cache 4 hours
  4-12h to resolution  →  cache 2 hours
  1-4h to resolution   →  cache 45 minutes
  < 1h to resolution   →  cache 15 minutes

Cache Invalidation:
  - TTL expires
  - Whale count increases by ≥2 (new convergence = new signal)
  - Manual force via API (future)
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import threading
import os


@dataclass
class CachedAnalysis:
    """Stores a cached Council analysis for a specific market."""
    market_id: str
    market_question: str
    final_score: float
    consensus_data: Dict          # Full council response (for DB logging)
    cached_at: datetime
    end_date: Optional[datetime]  # When the market resolves
    whale_count: int              # Whale count at time of analysis

    @property
    def ttl_seconds(self) -> int:
        """Dynamic TTL based on time remaining until market resolution."""
        if not self.end_date:
            return 4 * 3600  # 4 hours default if no end_date known

        now = datetime.now(timezone.utc)
        time_to_end = (self.end_date - now).total_seconds()

        if time_to_end <= 0:
            return 0              # Market already ended
        elif time_to_end < 1 * 3600:
            return 15 * 60        # < 1h → cache 15 min
        elif time_to_end < 4 * 3600:
            return 45 * 60        # 1-4h → cache 45 min
        elif time_to_end < 12 * 3600:
            return 2 * 3600       # 4-12h → cache 2 hours
        else:
            return 4 * 3600       # > 12h → cache 4 hours

    @property
    def is_expired(self) -> bool:
        elapsed = (datetime.now(timezone.utc) - self.cached_at).total_seconds()
        return elapsed > self.ttl_seconds

    @property
    def remaining_ttl_str(self) -> str:
        """Human-readable remaining TTL."""
        elapsed = (datetime.now(timezone.utc) - self.cached_at).total_seconds()
        remaining = max(0, self.ttl_seconds - elapsed)
        if remaining > 3600:
            return f"{remaining / 3600:.1f}h"
        elif remaining > 60:
            return f"{remaining / 60:.0f}m"
        else:
            return f"{remaining:.0f}s"


class CouncilCache:
    """
    Intelligent cache for Council AI analysis results.

    Prevents redundant OpenAI API calls by caching market analysis scores
    and re-evaluating decisions locally using cached scores + fresh prices.
    """

    def __init__(self):
        self._cache: Dict[str, CachedAnalysis] = {}
        self._lock = threading.Lock()

        # Daily budget tracking
        self._daily_call_count = 0
        self._daily_reset_date = datetime.now(timezone.utc).date()
        from app.core.config import settings
        self._max_daily_calls = settings.COUNCIL_MAX_DAILY_CALLS

        # Stats
        self._hits = 0
        self._misses = 0
        self._tokens_saved_estimate = 0

        logger.info(f"CouncilCache initialized (daily limit: {self._max_daily_calls} calls)")

    def get(self, market_id: str, current_whale_count: int = 0) -> Optional[CachedAnalysis]:
        """
        Look up a cached analysis for this market.

        Returns the CachedAnalysis if:
          1. Entry exists and TTL has not expired
          2. Whale count hasn't jumped by ≥2 (which signals new convergence)

        Returns None → caller should invoke the Council (cache miss).
        """
        with self._lock:
            entry = self._cache.get(market_id)

            if entry is None:
                self._misses += 1
                return None

            # Check TTL expiration
            if entry.is_expired:
                self._misses += 1
                logger.debug(
                    f"Cache EXPIRED: '{entry.market_question[:40]}…' "
                    f"(was cached {entry.ttl_seconds}s ago)"
                )
                del self._cache[market_id]
                return None

            # Check whale convergence change
            # If ≥2 more whales entered since we cached, the signal changed
            if current_whale_count > 0 and current_whale_count >= entry.whale_count + 2:
                self._misses += 1
                logger.info(
                    f"Cache INVALIDATED (new whales): '{entry.market_question[:40]}…' "
                    f"({entry.whale_count} → {current_whale_count} whales)"
                )
                del self._cache[market_id]
                return None

            # Cache HIT
            self._hits += 1
            self._tokens_saved_estimate += 4000  # ~4 agents × ~1000 tokens each

            logger.info(
                f"Cache HIT: '{entry.market_question[:40]}... ' "
                f"(score={entry.final_score:.3f}, TTL left={entry.remaining_ttl_str})"
            )
            return entry

    def store(
        self,
        market_id: str,
        market_question: str,
        final_score: float,
        consensus_data: Dict,
        end_date: Optional[str] = None,
        whale_count: int = 0,
    ):
        """Cache a Council analysis result."""
        # Parse end_date string → datetime
        end_dt = None
        if end_date:
            try:
                # Normalización forzada a UTC aware
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        entry = CachedAnalysis(
            market_id=market_id,
            market_question=market_question,
            final_score=final_score,
            consensus_data=consensus_data,
            cached_at=datetime.now(timezone.utc),
            end_date=end_dt,
            whale_count=whale_count,
        )

        with self._lock:
            self._cache[market_id] = entry
            self._increment_daily_count()

        logger.info(
            f"[CACHE] Cache STORED: '{market_question[:40]}…' "
            f"(score={final_score:.3f}, TTL={entry.ttl_seconds}s, whales={whale_count})"
        )

    def can_call_council(self) -> Tuple[bool, str]:
        """Check if we're within the daily OpenAI budget."""
        self._check_daily_reset()

        with self._lock:
            if self._daily_call_count >= self._max_daily_calls:
                return False, (
                    f"Daily AI budget exhausted "
                    f"({self._daily_call_count}/{self._max_daily_calls})"
                )
            remaining = self._max_daily_calls - self._daily_call_count
            return True, f"{remaining}/{self._max_daily_calls} calls remaining"

    # ── Helpers ─────────────────────────────────────────────

    def _increment_daily_count(self):
        self._check_daily_reset()
        self._daily_call_count += 1

    def _check_daily_reset(self):
        today = datetime.now(timezone.utc).date()
        if today != self._daily_reset_date:
            with self._lock:
                logger.info(
                    f"CouncilCache: Daily reset. "
                    f"Yesterday used {self._daily_call_count}/{self._max_daily_calls} Council calls."
                )
                self._daily_call_count = 0
                self._daily_reset_date = today

    def cleanup_expired(self):
        """Remove all expired entries. Call periodically."""
        with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired]
            for k in expired_keys:
                del self._cache[k]
        if expired_keys:
            logger.debug(f"CouncilCache: Cleaned up {len(expired_keys)} expired entries")

    def get_stats(self) -> Dict:
        """Return cache performance stats (for logging / monitoring)."""
        total_lookups = self._hits + self._misses
        hit_rate = (self._hits / total_lookups * 100) if total_lookups > 0 else 0

        # GPT-4o pricing: ~$2.50/1M input + $10/1M output ≈ ~$0.005 per council call
        cost_saved = self._daily_call_count * 0  # calls actually made cost money
        cost_saved = self._tokens_saved_estimate / 1000 * 0.005  # rough estimate

        return {
            "cached_markets": len(self._cache),
            "total_lookups": total_lookups,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "tokens_saved": f"~{self._tokens_saved_estimate:,}",
            "cost_saved": f"~${cost_saved:.2f}",
            "daily_calls": f"{self._daily_call_count}/{self._max_daily_calls}",
        }


# ── Global singleton ──────────────────────────────────────
council_cache = CouncilCache()
