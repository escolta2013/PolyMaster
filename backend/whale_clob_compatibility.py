"""
whale_clob_compatibility.py
============================
Pregunta: ¿Cuántas de nuestras 46 ballenas tienen al menos UN trade
en los últimos 30 días en mercados que pasan nuestros filtros CLOB?

Filtros CLOB: mid 0.25-0.75, spread < 0.15
Ventana: 30 días
"""
import asyncio
import httpx
import sys
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime, timedelta, timezone

# Lista completa de las 46 VIP wallets del tracker.py
ALL_VIP_WALLETS = [
    "0xc2e7800b5af46e6093872b177b7a5e7f0563be51",
    "0x507e52ef684ca2dd91f90a9d26d149dd3288beae",
    "0x07b8e44b90cc3e91b8d5fe60ea810d2534638e25",
    "0xee0d153c17fe82b8866b484753b56a700ab457ab",
    "0xa3e1664fc43903ac3010c89fa3dd00828f665968",
    "0x0b9cae2b0dfe7a71c413e0604eaac1c352f87e44",
    "0x22e4248bdb066f65c9f11cd66cdd3719a28eef1c",
    "0x715915950ffa56807ade2d75d742614321542660",
    "0x1667614321542660175174748465138472356787",
    "0x1030fc89f8e8bc61a232451064d15a3745944e7e",
    "0xfddfbfe715915950ffa56807ade2d75d74261432",
    "0x25e64cd559e8c46a888d8ebfa47d4490e810cc9f",
    "0x9c4ccdb83e6f78d84d5b4422917ca05752e23a00",
    "0xda9b03badde953167e7a861092b391580306fa50",
    "0x4959175440b8f38229b32f2f036057f6893ea6f5",
    "0x552337556e70f851bff6e0e97a2e00df7d5751e9",
    "0xe613b515bd46b1585a8b137a4d291d9b80bd540e",
    "0x50f3e0745cb8bef421bdaa403b1b70f5d1d8cfbf",
    "0x8df306b761d8e4f95ffa21a2d5d36fd330fe887a",
    "0x7abdf17e68380c9c4c90f84a0dc924592d9947d1",
    "0xed61f86bb5298d2f27c21c433ce58d80b88a9aa3",
    "0x257d0d66330654577734650715f5c46b540e3a03",
    "0x1abe1368601330a310162064e04d3c2628cb6497",
    "0x0b4731091ea7bf7920f358fd82b72e41a123a77b",
    "0x09abc5845c024a4f9a3abff29d95057e6b20e832",
    "0x1ce22666b8fb017a55db38c731b05d0b24583c96",
    "0xfe032d6324fd345a5c0569424a0207349964f14f",
    "0xf2be1c7b53567706288a25ee3b5d2abc58754c9f",
    "0xd5dca994eb0099f55b2dac334c7b9d76cb0411bb",
    "0xbb903888f2d952a1845c90142267c61b4926ad7f",
    "0x44de2a52d8d2d3ddcf39d58e315a10df53ba9c08",
    "0x2e29fc8a478a458d63028c88f3bc1e89bfa66572",
    "0x8f42ae0a01c0383c7ca8bd060b86a645ee74b88f",
    "0x7e6fda10646a4343358c84004859adfea1c0c022",
    "0x9ec7da81a2da3d47a47dd281b1ecf2cf2b3a35c0",
    "0xcd95ebd0d0d099fa442b9730991f2b8be5d28c17",
    "0xae7c98235d5dc797edfa3d3af2e0334238a4487e",
    "0x986b121c40e715167dde178b8520bf132a57bdc6",
    "0xbc43a2f0deb85ba4ad316300762972089c911540",
    "0xdfafd14f51d8f163a2df19144275233dc598aeb4",
    "0xc0292a841a0c9a7320aa39075cffcf1b8f64f705",
    "0xe617861a96631d7cefdb1ad43e95c33b5946f251",
    "0xc311bbe0d55797afa70c9329e15157640a6e44fc",
    "0xbb015bb4009b6a48bfb9363d9c9b1d54e9ab02e5",
    "0xc3e45193d37ec34b82129adfc46abff7bb415bf6",
    "0x9910712aacd5a9fe057e12b1d10a789b939f5058",
]

CLOB_MID_MIN   = 0.25
CLOB_MID_MAX   = 0.75
CLOB_MAX_SPREAD = 0.15
WINDOW_DAYS    = 30

def parse_ts(ts_val):
    if isinstance(ts_val, str):
        return datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
    return datetime.fromtimestamp(int(ts_val), tz=timezone.utc)

async def get_clob_spread(client, token_id):
    """Devuelve (mid, spread) o None si no hay libro."""
    if not token_id:
        return None
    try:
        r = await client.get(f"https://clob.polymarket.com/book?token_id={token_id}", timeout=5)
        if r.status_code != 200:
            return None
        b = r.json()
        bids, asks = b.get("bids", []), b.get("asks", [])
        if not bids or not asks:
            return None
        best_bid = float(bids[0]["price"])
        best_ask = float(asks[0]["price"])
        return (best_bid + best_ask) / 2, best_ask - best_bid
    except:
        return None

async def check_wallet(client, addr, now, since):
    """
    Obtiene los últimos 50 trades del wallet (hasta 30 días atrás)
    y verifica cuántos pasan los filtros CLOB actuales.
    """
    try:
        r = await client.get(
            "https://data-api.polymarket.com/v1/activity",
            params={"user": addr, "type": "TRADE", "limit": 50},
            timeout=10
        )
        data = r.json() if r.status_code == 200 else []
        if isinstance(data, dict):
            data = data.get("data", [])
    except:
        return {"addr": addr, "total": 0, "compatible": 0, "examples": []}

    # Filtrar por ventana de tiempo
    window_trades = []
    for act in data:
        try:
            ts = parse_ts(act.get("timestamp"))
            if ts >= since and act.get("side", "").upper() == "BUY":
                window_trades.append(act)
        except:
            continue

    # Verificar CLOB para cada trade (hasta 15 para no saturar la API)
    compatible = []
    semaphore_check = min(len(window_trades), 15)
    for trade in window_trades[:semaphore_check]:
        token_id = trade.get("asset", "")
        result = await get_clob_spread(client, token_id)
        if result is None:
            continue
        mid, spread = result
        if CLOB_MID_MIN <= mid <= CLOB_MID_MAX and spread <= CLOB_MAX_SPREAD:
            compatible.append({
                "token": token_id[:16],
                "mid": round(mid, 3),
                "spread": round(spread, 3),
                "price": round(float(trade.get("price", 0)), 3),
            })

    return {
        "addr": addr,
        "total_30d": len(window_trades),
        "clob_checked": semaphore_check,
        "compatible": len(compatible),
        "examples": compatible[:2],
    }

async def main():
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=WINDOW_DAYS)

    print("=" * 70)
    print(f"  WHALE CLOB COMPATIBILITY SCAN — {len(ALL_VIP_WALLETS)} wallets / {WINDOW_DAYS}d")
    print(f"  Filtros: mid [{CLOB_MID_MIN}-{CLOB_MID_MAX}], spread < {CLOB_MAX_SPREAD}")
    print("=" * 70)

    compatible_wallets = []
    zero_trades = []
    incompatible = []

    async with httpx.AsyncClient() as client:
        # Procesar en lotes de 8 para no saturar
        batch_size = 8
        for i in range(0, len(ALL_VIP_WALLETS), batch_size):
            batch = ALL_VIP_WALLETS[i:i+batch_size]
            tasks = [check_wallet(client, addr, now, since) for addr in batch]
            results = await asyncio.gather(*tasks)
            for r in results:
                addr_short = r["addr"][:22]
                if r["total_30d"] == 0:
                    zero_trades.append(r)
                    print(f"  {addr_short}...  INACTIVO (0 trades 30d)")
                elif r["compatible"] > 0:
                    compatible_wallets.append(r)
                    print(f"  {addr_short}...  {r['compatible']}/{r['clob_checked']} PASAN  [COMPATIBLE] ✅")
                else:
                    incompatible.append(r)
                    print(f"  {addr_short}...  0/{r['clob_checked']} pasan  ({r['total_30d']} trades, todos incompatibles)")

    print()
    print("=" * 70)
    print("  VEREDICTO FINAL")
    print("=" * 70)
    print(f"  Wallets con trades compatibles (>= 1 trade pasa CLOB): {len(compatible_wallets)}")
    print(f"  Wallets activos pero todos incompatibles:               {len(incompatible)}")
    print(f"  Wallets inactivos (0 trades en 30d):                    {len(zero_trades)}")
    print()

    if compatible_wallets:
        print("  WALLETS COMPATIBLES CON EL SISTEMA:")
        for r in compatible_wallets:
            print(f"    {r['addr'][:28]}  -> {r['compatible']} trades compatibles")
            for ex in r["examples"]:
                print(f"       mid={ex['mid']}  spread={ex['spread']}  price={ex['price']}")
        print()
        if len(compatible_wallets) >= 5:
            print("  DECISION: Suficientes wallets compatibles para un cluster detector funcional.")
            print("  => Usar solo estas wallets en el VIP list. Ampliar ventana a 48h.")
        elif len(compatible_wallets) >= 2:
            print("  DECISION: Pocos wallets compatibles. Cluster de 2+ es posible pero raro.")
            print("  => Cambiar ballenas (Opcion 3) + ampliar ventana a 48h.")
        else:
            print("  DECISION: Solo 1 wallet compatible. Cluster detector IMPOSIBLE.")
            print("  => Opcion 2: Abandonar Whale Tracker o hacer copy trading directo.")
    else:
        print("  DECISION: NINGUNA ballena opera en mercados compatibles con nuestros filtros.")
        print("  => Opcion 2 es la decision correcta. Abandona el Whale Tracker actual.")

if __name__ == "__main__":
    asyncio.run(main())
