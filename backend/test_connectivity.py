#!/usr/bin/env python3
"""
PolyMaster Connectivity Diagnostic
Prueba todas las conexiones sin ejecutar ningun trade.
"""
import os, httpx
from dotenv import load_dotenv
load_dotenv('.env')

print("=" * 60)
print("  POLYMASTER - DIAGNOSTICO DE CONECTIVIDAD")
print("=" * 60)

errors = []

# 1. Variables de entorno
print("\n[1/5] Variables de entorno")
pk          = os.getenv('PK', '')
supa_url    = os.getenv('SUPABASE_URL', '')
supa_key    = os.getenv('SUPABASE_KEY', '')
clob_key    = os.getenv('CLOB_API_KEY', '').strip()
clob_secret = os.getenv('CLOB_SECRET', '').strip()
clob_pass   = os.getenv('CLOB_PASSPHRASE', '').strip()
proxy       = os.getenv('POLY_PROXY_ADDRESS', '')
openai_key  = os.getenv('OPENAI_API_KEY', '')

def chk(name, val):
    if val:
        print(f"  OK  {name}: {val[:6]}...{val[-4:]} ({len(val)} chars)")
    else:
        print(f"  FALTA  {name}")
        errors.append(f"ENV faltante: {name}")

chk("PK", pk)
chk("SUPABASE_URL", supa_url)
chk("SUPABASE_KEY", supa_key)
chk("CLOB_API_KEY", clob_key)
chk("CLOB_SECRET", clob_secret)
chk("CLOB_PASSPHRASE", clob_pass)
print(f"  {'OK' if proxy else 'WARN'} POLY_PROXY_ADDRESS: {proxy[:12]+'...' if proxy else 'no config'}")
print(f"  {'OK' if openai_key else 'WARN'} OPENAI_API_KEY: {'configurado' if openai_key else 'no config (Council desactivado)'}")

# 2. APIs publicas
print("\n[2/5] APIs Publicas Polymarket")
for name, url in [
    ("CLOB API",  "https://clob.polymarket.com/markets?limit=1"),
    ("Gamma API", "https://gamma-api.polymarket.com/markets?limit=1"),
    ("Data API",  "https://data-api.polymarket.com/positions?limit=1"),
]:
    try:
        r = httpx.get(url, timeout=10)
        print(f"  OK  {name}: HTTP {r.status_code}")
    except Exception as e:
        print(f"  FAIL {name}: {e}")
        errors.append(f"API: {name}")

# 3. Autenticacion CLOB
print("\n[3/5] Autenticacion Polymarket L2 (CLOB)")
if not pk:
    print("  FAIL PK no configurado")
    errors.append("AUTH: sin PK")
else:
    try:
        from py_clob_client.client import ClobClient
        from py_clob_client.clob_types import ApiCreds
        from eth_account import Account

        acct = Account.from_key(pk)
        print(f"  EOA address  : {acct.address}")
        print(f"  Proxy address: {proxy or 'no configurado'}")

        auth_ok = False
        sig_types = [2, 1] if proxy else [0]

        for sig in sig_types:
            try:
                kwargs = dict(host='https://clob.polymarket.com', key=pk, chain_id=137, signature_type=sig)
                if proxy:
                    kwargs['funder'] = proxy
                client = ClobClient(**kwargs)

                if clob_key and clob_secret:
                    creds = ApiCreds(clob_key, clob_secret, clob_pass)
                    client.set_api_creds(creds)
                    print(f"  OK  sig_type={sig}: creds L2 del .env aceptadas")
                else:
                    creds = client.create_or_derive_api_creds()
                    client.set_api_creds(creds)
                    print(f"  OK  sig_type={sig}: creds L2 derivadas con exito")
                    print(f"      >>> Agrega al .env si no estan:")
                    print(f"      CLOB_API_KEY={creds.api_key}")
                    print(f"      CLOB_SECRET={creds.api_secret}")
                    print(f"      CLOB_PASSPHRASE={creds.api_passphrase}")

                auth_ok = True
                break
            except Exception as e:
                print(f"  WARN sig_type={sig} fallo: {str(e)[:100]}")

        if not auth_ok:
            errors.append("AUTH: fallo en todos los sig_type")

    except ImportError as e:
        print(f"  FAIL Dependencia faltante: {e}")
        errors.append(f"IMPORT: {e}")

# 4. Supabase
print("\n[4/5] Supabase")
if supa_url and supa_key:
    try:
        from supabase import create_client
        sb = create_client(supa_url, supa_key)
        for table in ['wallets', 'cluster_alerts', 'autonomous_logs', 'copy_trades']:
            try:
                sb.table(table).select('id').limit(1).execute()
                print(f"  OK  Tabla '{table}'")
            except Exception as e:
                print(f"  FAIL Tabla '{table}': {str(e)[:60]}")
                errors.append(f"Supabase tabla: {table}")
    except Exception as e:
        print(f"  FAIL Supabase conexion: {e}")
        errors.append("Supabase: conexion fallida")
else:
    print("  WARN Supabase no configurado")

# 5. Balance USDC on-chain
print("\n[5/5] Balance USDC on-chain (Polygon)")
if pk:
    try:
        from eth_account import Account
        from web3 import Web3
        check_addr = proxy if proxy else Account.from_key(pk).address
        w3 = Web3(Web3.HTTPProvider('https://polygon.llamarpc.com'))
        USDC = '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'
        abi  = [{'inputs':[{'name':'account','type':'address'}],'name':'balanceOf','outputs':[{'name':'','type':'uint256'}],'type':'function'}]
        bal  = w3.eth.contract(address=Web3.to_checksum_address(USDC), abi=abi)\
                 .functions.balanceOf(Web3.to_checksum_address(check_addr)).call() / 1e6
        print(f"  OK  USDC en {check_addr[:12]}...: ${bal:.4f}")
        if bal < 1:
            print("  WARN Balance muy bajo para operar (necesitas USDC depositado en Polymarket)")
    except Exception as e:
        print(f"  WARN Web3: {str(e)[:80]}")
else:
    print("  WARN Sin PK no se puede verificar balance")

# Resumen
print("\n" + "=" * 60)
if errors:
    print(f"RESULTADO: {len(errors)} problema(s) encontrado(s):")
    for e in errors:
        print(f"   * {e}")
else:
    print("RESULTADO: Todos los checks OK - sistema listo")
print("=" * 60)
