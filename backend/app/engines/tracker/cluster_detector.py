from loguru import logger
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
import asyncio
import httpx
from app.core.config import settings
from supabase import create_client, Client

@dataclass
class ClusterAlert:
    """Represents a cluster event: ≥N whales on same outcome."""
    market_id: str
    market_question: str
    token_id: str
    outcome: str                # "YES" or "NO"
    wallets: List[str]          # addresses involved
    wallet_grades: List[str]    # parallel list of grades
    wallet_count: int = 0
    avg_position_size: float = 0.0
    total_exposure: float = 0.0
    confidence: float = 0.0     # 0-1 score derived from quality
    detected_at: str = ""
    alert_id: str = ""
    end_date: Optional[str] = None

    def __post_init__(self):
        self.wallet_count = len(self.wallets)
        if not self.detected_at:
            self.detected_at = datetime.now(timezone.utc).isoformat()
            ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
            self.alert_id = f"cluster_{self.market_id[:8]}_{ts}"

class ClusterDetector:
    """
    Scans tracked smart-money wallets for convergence on the same market outcome.
    Focuses on REAL-TIME activity (last 12h) to find movements.
    """
    SMART_TIERS = {"WHALE", "SHARK", "ORCA"}

    def __init__(self, min_wallets: int = 2):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.min_wallets = min_wallets
        self._recent_alerts: Dict[str, datetime] = {}
        self.dedup_window = timedelta(hours=settings.CLUSTER_DEDUP_WINDOW_HOURS) # Dedup per outcome
        self.max_concurrent_requests = 10
        self._initialized = False

    async def _ensure_initialized(self):
        if self._initialized: return
        await self._load_recent_alerts_from_db()
        self._initialized = True

    async def _load_recent_alerts_from_db(self):
        try:
            since = (datetime.now(timezone.utc) - self.dedup_window).isoformat()
            resp = self.supabase.table("cluster_alerts")\
                .select("market_id, outcome, detected_at")\
                .gte("detected_at", since)\
                .execute()
            
            count = 0
            for row in (resp.data or []):
                key = f"{row['market_id']}_{row['outcome']}"
                dt = datetime.fromisoformat(row['detected_at'].replace("Z", "+00:00"))
                self._recent_alerts[key] = dt
                count += 1
            logger.info(f"ClusterDetector: Hydrated {count} recent alerts mapping.")
        except Exception as e:
            logger.error(f"Failed to hydrate: {e}")

    async def _load_smart_wallets(self) -> List[Dict]:
        try:
            # Table is 'wallets' in our schema, not 'smart_money'
            resp = self.supabase.table("wallets")\
                .select("address, grade")\
                .eq("is_smart_money", True)\
                .execute()
            return resp.data or []
        except Exception as e:
            logger.error(f"Failed to load smart wallets: {e}")
            return []

    async def _fetch_wallet_activity(self, client: httpx.AsyncClient, wallet: Dict, semaphore: asyncio.Semaphore) -> List[Dict]:
        async with semaphore:
            addr = wallet["address"]
            try:
                url = f"{settings.DATA_API_URL}/activity"
                params = {"user": addr, "type": "TRADE", "limit": 30}
                resp = await client.get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    # The endpoint might return {"data": [...]} or just [...] depending on version
                    if isinstance(data, dict):
                        data = data.get("data", [])
                    now = datetime.now(timezone.utc)
                    recent = []
                    for act in data:
                        try:
                            ts_val = act.get("timestamp")
                            if not ts_val:
                                continue
                            if isinstance(ts_val, str):
                                ts = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
                            else:
                                ts = datetime.fromtimestamp(int(ts_val), tz=timezone.utc)
                                
                            if now - ts < timedelta(hours=settings.CLUSTER_ACTIVITY_WINDOW_HOURS):
                                recent.append(act)
                        except: continue
                    return recent
            except: pass
            return []

    async def scan_for_clusters(self) -> List[ClusterAlert]:
        await self._ensure_initialized()
        logger.info("Whale Tracker: Scanning for real-time movements (Activity feed)...")
        smart_wallets = await self._load_smart_wallets()
        if not smart_wallets: return []

        # (token_id, outcome) -> [{ address, grade, size, ts }]
        convergence: Dict[str, List[Dict[str, Any]]] = {}
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        async with httpx.AsyncClient() as client:
            tasks = [self._fetch_wallet_activity(client, w, semaphore) for w in smart_wallets]
            results = await asyncio.gather(*tasks)

            for wallet_data, trades in zip(smart_wallets, results):
                for trade in trades:
                    token_id = trade.get("asset")
                    outcome = trade.get("outcome", "YES").upper()
                    side = trade.get("side", "BUY").upper()
                    if not token_id or side != "BUY": continue
                    
                    key = f"{token_id}_{outcome}"
                    if key not in convergence: convergence[key] = []
                    
                    if not any(v['address'] == wallet_data['address'] for v in convergence[key]):
                        convergence[key].append({
                            "address": wallet_data["address"],
                            "grade": wallet_data["grade"],
                            "size": float(trade.get("amount", 0))
                        })

        new_alerts = []
        async with httpx.AsyncClient() as client:
            for key, participants in convergence.items():
                if len(participants) < self.min_wallets: continue
                
                token_id, outcome = key.split("_")
                if key in self._recent_alerts: continue

                # Deep CLOB Filtering for Whales (Price X-Y, Spread dynamic)
                # Whales have a wider price tolerance but strict spread limits
                # In Paper Trading Mode, spread is relaxed for calibration data
                whale_max_spread = settings.PAPER_TRADING_MAX_SPREAD if settings.PAPER_TRADING_MODE else settings.CLUSTER_WHALE_MAX_SPREAD
                try:
                    resp = await client.get(f"https://clob.polymarket.com/book?token_id={token_id}")
                    if resp.status_code == 200:
                        book = resp.json()
                        bids = book.get("bids", [])
                        asks = book.get("asks", [])
                        if not bids or not asks: 
                            continue
                            
                        best_bid = float(bids[0].get("price", 0))
                        best_ask = float(asks[0].get("price", 1))
                        midpoint = (best_bid + best_ask) / 2.0
                        
                        if midpoint < settings.CLUSTER_PRICE_LOW or midpoint > settings.CLUSTER_PRICE_HIGH:
                            continue
                        if spread > whale_max_spread:
                            continue
                    else:
                        continue # If we can't get the book, skip to be safe
                except Exception as e:
                    logger.warning(f"Whale Tracker CLOB fail for {token_id}: {e}")
                    continue

                # Resolve real market metadata from CLOB API using token_id
                # Without this, the Director receives a placeholder market_id that
                # never matches Gamma API → always returns "market_not_found".
                real_market_id = token_id  # Fallback: Director can also look up by token_id
                real_question = "Whale Movement Detected"
                real_end_date = None
                try:
                    mkt_resp = await client.get(
                        f"https://clob.polymarket.com/markets/{token_id}",
                        timeout=5
                    )
                    if mkt_resp.status_code == 200:
                        mkt_data = mkt_resp.json()
                        # CLOB /markets/<token_id> returns the condition_id
                        real_market_id = mkt_data.get("condition_id") or token_id
                        real_question = mkt_data.get("question") or "Whale Movement Detected"
                        real_end_date = mkt_data.get("end_date_iso") or mkt_data.get("game_start_time")
                        logger.debug(
                            f"Whale Tracker: Resolved token {token_id[:8]}... → "
                            f"market '{real_question[:40]}' (id={real_market_id[:8]}...)"
                        )
                except Exception as mkt_e:
                    logger.debug(f"Whale Tracker: Could not resolve market for token {token_id[:8]}: {mkt_e}")

                alert = ClusterAlert(
                    market_id=real_market_id,
                    market_question=real_question,
                    token_id=token_id,
                    outcome=outcome,
                    wallets=[p['address'] for p in participants],
                    wallet_grades=[p['grade'] for p in participants],
                    total_exposure=sum(p['size'] for p in participants),
                    avg_position_size=sum(p['size'] for p in participants) / len(participants),
                    confidence=self._calculate_confidence(participants),
                    end_date=real_end_date,
                )
                
                new_alerts.append(alert)
                self._recent_alerts[key] = datetime.now(timezone.utc)
                await self._persist_alert(alert)

        logger.info(f"Whale Tracker: Found {len(new_alerts)} real-time clusters.")
        return new_alerts

    def _calculate_confidence(self, participants: List[Dict]) -> float:
        base = settings.CLUSTER_BASE_CONFIDENCE # Start higher for activity
        if len(participants) >= 3: base += 0.2
        if any(p['grade'] == "WHALE" for p in participants): base += 0.15
        return min(base, 0.99)

    async def _persist_alert(self, alert: ClusterAlert):
        try:
            self.supabase.table("cluster_alerts").insert({
                "market_id": alert.market_id,
                "token_id": alert.token_id,
                "outcome": alert.outcome,
                "confidence": alert.confidence,
                "wallet_count": alert.wallet_count,
                "detected_at": alert.detected_at,
                "alert_id": alert.alert_id
            }).execute()
        except Exception as e:
            logger.error(f"Persist error: {e}")
