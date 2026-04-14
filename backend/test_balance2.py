import asyncio
from app.core.config import settings
from app.core.client import PolyClient

async def main():
    try:
        p_client = PolyClient.get_instance()
    except Exception as e:
        print(f"Error getting PolyClient instance: {e}")
        return

    print("Owner Address (from settings):", settings.POLY_PROXY_ADDRESS)
    try:
        if p_client.sdk:
            proxy = getattr(p_client.sdk, "proxy_wallet_address", None)
            if not proxy: # fallback if method is different
               proxy = p_client.sdk.derive_proxy_wallet_address()
            print("Real Polymarket Proxy Address:", proxy)
        else:
            print("No SDK")
    except Exception as e:
        print("Error getting proxy:", e)

if __name__ == "__main__":
    asyncio.run(main())
