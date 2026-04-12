from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCredentials
from app.core.config import settings
import asyncio

async def diagnose():
    print('\n--- 🔍 DIAGNÓSTICO DE CONEXIÓN JAPÓN ---')
    print(f'Proxy Detectado: {settings.POLY_PROXY_ADDRESS}')
    
    # Probamos Signature Type 1 y 2
    for sig_type in [1, 2]:
        print(f'\nProbando Signature Type: {sig_type}...')
        try:
            # En algunas versiones ApiCredentials está en .clob_types, en otras en .client
            # Vamos a pasar un diccionario para evitar errores de importación
            creds = {
                "api_key": settings.CLOB_API_KEY,
                "secret": settings.CLOB_SECRET,
                "passphrase": settings.CLOB_PASSPHRASE,
                "signature_type": sig_type,
                "funder": settings.POLY_PROXY_ADDRESS
            }
            client = ClobClient('https://clob.polymarket.com', key=settings.PK, credentials=creds)
            resp = client.get_orders()
            print(f'✅ ¡ÉXITO CON TIPO {sig_type}!')
            return
        except Exception as e:
            print(f'❌ Falló Tipo {sig_type}: {e}')

    print('\n--- 🔬 PRUEBA ADICIONAL (EOA FUNDER) ---')
    try:
        creds = {
            "api_key": settings.CLOB_API_KEY,
            "secret": settings.CLOB_SECRET,
            "passphrase": settings.CLOB_PASSPHRASE,
            "signature_type": 2,
            "funder": '0x62d3200Dc069743e0D8A440D03985c5133A43eD8'
        }
        client = ClobClient('https://clob.polymarket.com', key=settings.PK, credentials=creds)
        resp = client.get_orders()
        print(f'✅ ¡ÉXITO CON EOA COMO FUNDER!')
    except Exception as e:
        print(f'❌ Falló todo: {e}')

if __name__ == "__main__":
    asyncio.run(diagnose())
