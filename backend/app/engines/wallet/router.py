from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from app.engines.wallet.manager import wallet_manager
from app.core.logging import logger
from app.api.auth import verify_admin_key

router = APIRouter(prefix="/wallet", tags=["Wallet Manager"])

@router.get("/status/{user_id}")
async def get_wallet_status(user_id: str):
    """Checks if a user has a proxy wallet and returns basic info."""
    wallet = wallet_manager.get_user_wallet(user_id)
    if not wallet:
        return {"has_wallet": False, "address": None, "balance": 0.0}
    
    return {
        "has_wallet": True,
        "address": wallet["proxy_address"],
        "balance": wallet.get("balance_usdc", 0.0),
        "created_at": wallet.get("created_at")
    }

@router.post("/generate/{user_id}")
async def generate_wallet(user_id: str):
    """Generates a new proxy wallet for the user if they don't have one."""
    existing = wallet_manager.get_user_wallet(user_id)
    if existing:
        raise HTTPException(status_code=400, detail="User already has a proxy wallet")
    
    try:
        result = wallet_manager.generate_proxy_wallet(user_id)
        return result
    except Exception as e:
        logger.error(f"Error generating wallet for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/balance/{user_id}")
async def refresh_balance(user_id: str):
    """Refreshes and returns the on-chain USDC balance for a user's wallet."""
    wallet = wallet_manager.get_user_wallet(user_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    balance = wallet_manager.get_onchain_balance(wallet["proxy_address"])
    return {"address": wallet["proxy_address"], "balance": balance}

@router.post("/withdraw/{user_id}")
async def withdraw(user_id: str, data: Dict[str, Any], key: str = Depends(verify_admin_key)):
    """Withdraws USDC from proxy wallet to a target address. Requires X-API-KEY."""
    target = data.get("address")
    amount = data.get("amount")
    
    if not target or not amount:
        raise HTTPException(status_code=400, detail="Address and amount required")
    
    try:
        tx_hash = wallet_manager.withdraw_usdc(user_id, target, float(amount))
        return {"status": "success", "tx_hash": tx_hash}
    except Exception as e:
        logger.error(f"Withdrawal error for {user_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
