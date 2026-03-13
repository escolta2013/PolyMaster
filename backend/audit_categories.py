"""
audit_categories.py
Extiende evaluate_sim_profit.py con clasificación por categorías.
Calcula el accuracy REAL post-filtro (mercados que seguiremos operando)
vs las categorías excluidas (eSports, fútbol directo, precio específico).
"""
import os, sys, httpx, asyncio
from typing import Optional, List, Dict
from collections import defaultdict

# Fix Windows console encoding
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath("."))
from app.core.config import settings
from supabase import create_client


async def fetch_final_price(market_id: str) -> Optional[float]:
    """Consulta Gamma API para obtener el precio actual (proxy de resolución)."""
    try:
        url = f"https://gamma-api.polymarket.com/markets/{market_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
            if resp.status_code == 200:
                return resp.json().get("bestAsk")
    except Exception:
        pass
    return None


def categorize(q: str) -> str:
    ql = q.lower()
    esports_kw = [
        "dota 2", "counter-strike", "valorant", "lol:", "league of legends",
        "map 1 winner", "map 2 winner", "map handicap", "esports",
        "astral", "mindfreak", "bounty hunters esports",
    ]
    if any(k in ql for k in esports_kw):
        return "EXCLUIDA_ESPORTS"
    if ("win on 2026-" in ql
            and "both teams" not in ql
            and "o/u" not in ql
            and "spread" not in ql):
        return "EXCLUIDA_FUTBOL"
    price_kw = [
        "close above $", "close below $", "be above $", "be below $",
        "be between $", "nvidia", "nvda", "share price", "stock price",
        "above $180", "above $66,000", "above $100,000",
    ]
    if any(k in ql for k in price_kw):
        return "EXCLUIDA_PRECIO"
    return "MANTENIDA"


async def run_audit():
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    # Fetch unique WOULD_EXECUTE markets (first entry per market = entry price)
    res = supabase.table("autonomous_logs") \
        .select("market_id, market_question, best_ask, council_score, detected_at") \
        .eq("decision", "WOULD_EXECUTE") \
        .order("detected_at", desc=False) \
        .execute()

    rows = res.data or []

    # Group: one entry per market_id (earliest = entry price)
    seen = {}
    for r in rows:
        mid = r["market_id"]
        if mid not in seen and r.get("best_ask"):
            seen[mid] = r

    unique_markets = list(seen.values())
    print(f"\nMercados únicos evaluados: {len(unique_markets)}")
    print("Consultando precios actuales en Gamma API (puede tardar ~30s)...\n")

    # Buckets
    results: Dict[str, Dict[str, List]] = {
        "MANTENIDA":         {"WIN": [], "LOSS": [], "PENDING": []},
        "EXCLUIDA_ESPORTS":  {"WIN": [], "LOSS": [], "PENDING": []},
        "EXCLUIDA_FUTBOL":   {"WIN": [], "LOSS": [], "PENDING": []},
        "EXCLUIDA_PRECIO":   {"WIN": [], "LOSS": [], "PENDING": []},
    }

    for m in unique_markets:
        mid       = m["market_id"]
        q         = m["market_question"]
        entry     = float(m.get("best_ask") or 0)
        cat       = categorize(q)

        final = await fetch_final_price(mid)
        if final is None:
            results[cat]["PENDING"].append(q)
            continue
        final = float(final)

        if final >= 0.97:
            results[cat]["WIN"].append((q, entry, final))
        elif final <= 0.03:
            results[cat]["LOSS"].append((q, entry, final))
        else:
            results[cat]["PENDING"].append(q)

    # ── Print Summary ──────────────────────────────────────────────────────
    LINE = "=" * 72
    print(LINE)

    total_wins   = sum(len(results[c]["WIN"])  for c in results)
    total_losses = sum(len(results[c]["LOSS"]) for c in results)
    total_res    = total_wins + total_losses
    print(f"  ACCURACY GLOBAL (agregado histórico, todos)")
    print(f"  Wins: {total_wins} | Losses: {total_losses} | Resueltos: {total_res}")
    if total_res:
        print(f"  Accuracy: {total_wins / total_res * 100:.1f}%")

    print()

    # Excluidas en bloque
    exc_wins   = sum(len(results[c]["WIN"])  for c in results if c != "MANTENIDA")
    exc_losses = sum(len(results[c]["LOSS"]) for c in results if c != "MANTENIDA")
    exc_total  = exc_wins + exc_losses
    print(f"  CATEGORÍAS EXCLUIDAS (ruido eliminado del pipeline)")
    print(f"  Wins: {exc_wins} | Losses: {exc_losses} | Resueltos: {exc_total}")
    if exc_total:
        print(f"  Accuracy de excluidas: {exc_wins / exc_total * 100:.1f}%  ← justifica la exclusión")

    print()

    # Mantenidas
    kw  = len(results["MANTENIDA"]["WIN"])
    kl  = len(results["MANTENIDA"]["LOSS"])
    kt  = kw + kl
    kp  = len(results["MANTENIDA"]["PENDING"])
    print(f"  CATEGORÍAS MANTENIDAS → ACCURACY REAL DEL SISTEMA POST-FILTRO")
    print(f"  Wins: {kw} | Losses: {kl} | Resueltos: {kt} | Aún abiertos: {kp}")
    if kt:
        acc = kw / kt * 100
        delta = acc - 60.0
        estado = "✅ SOBRE META (60%)" if delta >= 0 else f"⚠️  A {abs(delta):.1f}pp de la meta de 60%"
        print(f"  ✅ Accuracy Post-Filtro: {acc:.1f}%  → {estado}")

    print()
    print(LINE)

    # Detalle por subcategoría
    for cat_key, label in [
        ("MANTENIDA",        "MANTENIDA"),
        ("EXCLUIDA_ESPORTS", "EXCLUIDA — eSports"),
        ("EXCLUIDA_FUTBOL",  "EXCLUIDA — Fútbol Directo"),
        ("EXCLUIDA_PRECIO",  "EXCLUIDA — Precio Específico"),
    ]:
        wins_l  = results[cat_key]["WIN"]
        losses_l = results[cat_key]["LOSS"]
        n = len(wins_l) + len(losses_l)
        if n == 0:
            continue
        acc_str = f"{len(wins_l)/n*100:.0f}%" if n else "—"
        print(f"\n  [{label}]  {len(wins_l)}W / {len(losses_l)}L  (Acc: {acc_str})")
        for q, entry, final in wins_l:
            print(f"    ✅ WIN   entry={entry:.3f}  final={final:.3f}  | {q[:60]}")
        for q, entry, final in losses_l:
            print(f"    ❌ LOSS  entry={entry:.3f}  final={final:.3f}  | {q[:60]}")

    print(f"\n{LINE}")


if __name__ == "__main__":
    asyncio.run(run_audit())
