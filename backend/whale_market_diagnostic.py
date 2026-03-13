"""
whale_market_diagnostic.py
==========================
Responde la pregunta crítica:
"¿En qué mercados están operando nuestras ballenas y pasarían nuestros filtros CLOB?"

Analiza las últimas 72h de actividad de las TOP 15 ballenas y por cada trade:
1. Obtiene el precio del mercado en el CLOB
2. Verifica si pasaría nuestros filtros (mid 0.25-0.75, spread ≤ 0.15)
3. Reporta qué porcentaje de operaciones reales JAMÁS llega al detector

Resultado esperado:
- Si >50% de trades fallan el filtro CLOB → problema de incompatibilidad de estrategia
- Si <20% fallan → el problema es la ventana de 12h, hay que expandir a 24-48h
"""
import asyncio
import httpx
import sys
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# Top 15 ballenas verificadas (las de mayor PnL del Leaderboard)
TOP_WHALES = [
    ("0xc2e7800b5af46e6093872b177b7a5e7f0563be51", "beachboy4 $351K"),
    ("0x07b8e44b90cc3e91b8d5fe60ea810d2534638e25", "joosangyoo $150K"),
    ("0xee0d153c17fe82b8866b484753b56a700ab457ab", "BBPK $102K"),
    ("0xa3e1664fc43903ac3010c89fa3dd00828f665968", "sd13 $61K"),
    ("0x25e64cd559e8c46a888d8ebfa47d4490e810cc9f", "Dune $624K"),
    ("0x9c4ccdb83e6f78d84d5b4422917ca05752e23a00", "Dune $547K"),
    ("0xda9b03badde953167e7a861092b391580306fa50", "Dune $491K"),
    ("0xed61f86bb5298d2f27c21c433ce58d80b88a9aa3", "Dune $370K"),
    ("0x257d0d66330654577734650715f5c46b540e3a03", "Dune $359K"),
    ("0x1abe1368601330a310162064e04d3c2628cb6497", "Dune $322K"),
    ("0x0b4731091ea7bf7920f358fd82b72e41a123a77b", "Dune $302K"),
    ("0xf2be1c7b53567706288a25ee3b5d2abc58754c9f", "Dune $277K"),
    ("0xd5dca994eb0099f55b2dac334c7b9d76cb0411bb", "Dune $271K"),
    ("0x44de2a52d8d2d3ddcf39d58e315a10df53ba9c08", "Dune $249K"),
    ("0x9910712aacd5a9fe057e12b1d10a789b939f5058", "Dune $230K"),
]

CLOB_MID_MIN = 0.25
CLOB_MID_MAX = 0.75
CLOB_MAX_SPREAD = 0.15
WINDOW_HOURS = 72  # Miramos 72h para tener suficientes datos

def parse_timestamp(ts_val):
    if isinstance(ts_val, str):
        return datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
    return datetime.fromtimestamp(int(ts_val), tz=timezone.utc)


async def get_clob_info(client: httpx.AsyncClient, token_id: str) -> dict | None:
    """Obtiene precio y spread del CLOB para un token."""
    if not token_id:
        return None
    try:
        resp = await client.get(
            f"https://clob.polymarket.com/book?token_id={token_id}",
            timeout=5
        )
        if resp.status_code != 200:
            return None
        book = resp.json()
        bids = book.get("bids", [])
        asks = book.get("asks", [])
        if not bids or not asks:
            return None
        best_bid = float(bids[0]["price"])
        best_ask = float(asks[0]["price"])
        mid = (best_bid + best_ask) / 2
        spread = best_ask - best_bid
        return {"mid": mid, "spread": spread, "bid": best_bid, "ask": best_ask}
    except:
        return None


async def analyze_whale(client: httpx.AsyncClient, addr: str, label: str, now: datetime) -> dict:
    """Obtiene trades de los últimos 72h y verifica filtros CLOB."""
    since = now - timedelta(hours=WINDOW_HOURS)
    
    try:
        resp = await client.get(
            "https://data-api.polymarket.com/v1/activity",
            params={"user": addr, "type": "TRADE", "limit": 50},
            timeout=10
        )
        if resp.status_code != 200:
            return {"label": label, "error": f"HTTP {resp.status_code}"}
        
        data = resp.json()
        if isinstance(data, dict):
            data = data.get("data", [])
    except Exception as e:
        return {"label": label, "error": str(e)}
    
    trades_in_window = []
    for act in data:
        try:
            ts = parse_timestamp(act.get("timestamp"))
            if ts >= since and act.get("side", "").upper() == "BUY":
                trades_in_window.append(act)
        except:
            continue
    
    # Para cada trade en ventana, verificar CLOB
    passed = []
    failed_mid = []
    failed_spread = []
    no_clob = []
    
    # Limit concurrent CLOB lookups
    for trade in trades_in_window[:20]:  # max 20 trades per whale
        token_id = trade.get("asset", "")
        price = float(trade.get("price", 0))
        
        clob = await get_clob_info(client, token_id)
        
        if clob is None:
            no_clob.append({"price": price, "token": token_id[:12]})
            continue
            
        mid = clob["mid"]
        spread = clob["spread"]
        
        trade_info = {
            "price": price,
            "mid": round(mid, 3),
            "spread": round(spread, 3),
            "token": token_id[:12],
            "outcome": trade.get("outcome", "?"),
        }
        
        if mid < CLOB_MID_MIN or mid > CLOB_MID_MAX:
            failed_mid.append(trade_info)
        elif spread > CLOB_MAX_SPREAD:
            failed_spread.append(trade_info)
        else:
            passed.append(trade_info)
    
    total = len(passed) + len(failed_mid) + len(failed_spread) + len(no_clob)
    
    return {
        "label": label,
        "addr": addr[:20],
        "trades_72h": len(trades_in_window),
        "clob_checked": total,
        "passed": passed,
        "failed_mid": failed_mid,
        "failed_spread": failed_spread,
        "no_clob": no_clob,
    }


async def main():
    now = datetime.now(timezone.utc)
    print("=" * 70)
    print(f"  WHALE MARKET DIAGNOSTIC")
    print(f"  Ventana: ultimas {WINDOW_HOURS}h | Filtros: mid[{CLOB_MID_MIN}-{CLOB_MID_MAX}] spread<{CLOB_MAX_SPREAD}")
    print("=" * 70)
    
    results = []
    async with httpx.AsyncClient() as client:
        for addr, label in TOP_WHALES:
            print(f"  Analizando {label}...", end=" ", flush=True)
            r = await analyze_whale(client, addr, label, now)
            results.append(r)
            if "error" in r:
                print(f"ERROR: {r['error']}")
            else:
                total = r["clob_checked"]
                passed = len(r["passed"])
                pass_rate = (passed / total * 100) if total > 0 else 0
                print(f"{r['trades_72h']} trades 72h | {total} CLOB checked | {passed}/{total} PASAN ({pass_rate:.0f}%)")
    
    print()
    print("=" * 70)
    print("  RESUMEN GLOBAL")
    print("=" * 70)
    
    total_trades = sum(r.get("trades_72h", 0) for r in results if "error" not in r)
    total_clob = sum(r.get("clob_checked", 0) for r in results if "error" not in r)
    total_passed = sum(len(r["passed"]) for r in results if "error" not in r)
    total_failed_mid = sum(len(r["failed_mid"]) for r in results if "error" not in r)
    total_failed_spread = sum(len(r["failed_spread"]) for r in results if "error" not in r)
    total_no_clob = sum(len(r["no_clob"]) for r in results if "error" not in r)
    
    print(f"  Trades totales 72h:           {total_trades}")
    print(f"  Trades verificados en CLOB:   {total_clob}")
    print(f"  PASAN filtros (actionable):   {total_passed} ({total_passed/total_clob*100:.1f}%)" if total_clob else "  N/A")
    print(f"  FALLAN por precio mid:         {total_failed_mid}")
    print(f"  FALLAN por spread alto:        {total_failed_spread}")
    print(f"  Sin datos CLOB (expirado?):   {total_no_clob}")
    print()
    
    if total_clob > 0:
        pass_pct = total_passed / total_clob * 100
        if pass_pct > 50:
            print("  DIAGNOSTICO: Las ballenas si operan en mercados viables.")
            print("  => Problema es la ventana 12h. SOLUCION: Ampliar a 24-48h.")
        elif pass_pct > 20:
            print("  DIAGNOSTICO: Filtros eliminan muchas oportunidades pero no todas.")
            print("  => Combinar: ampliar ventana + revisar filtros CLOB para whales.")
        else:
            print("  DIAGNOSTICO: La mayoria de trades de ballenas FALLA nuestros filtros.")
            print("  => Problema de incompatibilidad de estrategia. Los whales operan en")
            print("     mercados muy sesgados (>0.75) o iliquidos que descartamos.")
            print("  => Considerar filtros diferenciados para señales whale vs. indexer.")
    
    # Muestra ejemplos de trades que PASAN para entender qué mercados son
    passing_examples = []
    for r in results:
        if "error" not in r:
            for t in r["passed"][:2]:
                passing_examples.append((r["label"], t))
    
    if passing_examples:
        print()
        print("  EJEMPLOS DE TRADES QUE PASAN FILTROS:")
        for label, t in passing_examples[:8]:
            print(f"    {label[:20]:20} mid={t['mid']:.3f} spread={t['spread']:.3f} price={t['price']:.3f}")
    
    # Muestra ejemplos de trades que FALLAN
    failing_examples = []
    for r in results:
        if "error" not in r:
            for t in r["failed_mid"][:1]:
                failing_examples.append((r["label"], t, "MID"))
            for t in r["failed_spread"][:1]:
                failing_examples.append((r["label"], t, "SPREAD"))
    
    if failing_examples:
        print()
        print("  EJEMPLOS DE TRADES QUE FALLAN FILTROS:")
        for label, t, reason in failing_examples[:8]:
            print(f"    {label[:20]:20} mid={t['mid']:.3f} spread={t['spread']:.3f} price={t['price']:.3f}  <- FALLA {reason}")

    print()
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
