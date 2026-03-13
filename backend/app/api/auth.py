from fastapi import HTTPException, Header
from app.core.config import settings

async def verify_admin_key(x_api_key: str = Header(...)):
    """Simple API Key verification for admin endpoints."""
    if x_api_key != settings.MASTER_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key")
    return x_api_key
