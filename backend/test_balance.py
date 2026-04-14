import asyncio
from app.core.config import settings
from app.core.client import PolyClient
from app.engines.wallet.manager import wallet_manager
from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
from eth_account import Account

async def main():
    try:
        p_client = PolyClient.get_instance()
    except Exception as e:
        print(f"Error getting PolyClient instance: {e}")
        p_client = None
    
    # 1. CLOB Balance
    clob_bal = 0.0
    try:
        if p_client and p_client.sdk:
            r = p_client.sdk.get_balance_allowance(BalanceAllowanceParams(asset_type=AssetType.COLLATERAL))
            print(f"CLOB Raw: {r}")
            clob_bal = float(r.get("balance", 0)) / 10**6
            print(f"CLOB USD: {clob_bal}")
        else:
            print("PolyClient not fully initialized")
    except Exception as e:
        print(f"CLOB Error: {e}")
        
    # 2. Chain Balance
    target_address = settings.POLY_PROXY_ADDRESS if hasattr(settings, 'POLY_PROXY_ADDRESS') and settings.POLY_PROXY_ADDRESS else Account.from_key(settings.PK).address
    print(f"Target address: {target_address}")
    chain_bal = 0.0
    try:
        chain_bal = wallet_manager.get_onchain_balance(target_address)
        print(f"Chain USD: {chain_bal}")
    except Exception as e:
        print(f"Chain Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
