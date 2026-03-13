from fastapi import APIRouter, HTTPException, Depends
from typing import Dict
from app.core.config import settings
from app.core.logging import logger
from app.api.auth import verify_admin_key

router = APIRouter(prefix="/director", tags=["Autonomous Brain"])

# In-memory override for runtime control
RUNTIME_OVERRIDE = {
    "enabled": settings.ENABLE_AUTONOMOUS_TRADING
}

@router.get("/status")
async def get_status(key: str = Depends(verify_admin_key)):
    """Returns the current state of the Autonomous Brain."""
    return {
        "enabled": RUNTIME_OVERRIDE["enabled"],
        "confidence_threshold": settings.AUTONOMOUS_CONFIDENCE_THRESHOLD,
        "max_size": settings.AUTONOMOUS_MAX_SIZE,
        "system_wallet": settings.AUTONOMOUS_USER_ID or "NOT_CONFIGURED"
    }

@router.post("/toggle")
async def toggle_brain(data: Dict[str, bool], key: str = Depends(verify_admin_key)):
    """Enables or disables the Autonomous Director at runtime."""
    new_state = data.get("enabled")
    if new_state is None:
        raise HTTPException(status_code=400, detail="Missing 'enabled' field")
    
    RUNTIME_OVERRIDE["enabled"] = new_state
    
    # Update the Director instance dynamically
    from app.engines.autonomous.director import director
    
    logger.warning(f"⚠️ Autonomous Brain Toggled: {'ON' if new_state else 'OFF'}")
    return {"status": "updated", "enabled": new_state}
