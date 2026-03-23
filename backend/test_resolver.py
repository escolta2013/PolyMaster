import asyncio
import os
import sys
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.getcwd())

from app.core.config import settings
from supabase import create_client

async def test():
    sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    # Try to fetch one pending trade
    res = sb.table("autonomous_logs").select("*").eq("correct", "PENDING").limit(1).execute()
    print(f"Fetch success: {len(res.data) > 0}")
    if res.data:
        row = res.data[0]
        # Try to update it to PENDING again (no-op but tests the path)
        try:
            upd_res = sb.table("autonomous_logs").update({"correct": "PENDING"}).eq("id", row["id"]).execute()
            print("Update success")
        except Exception as e:
            print(f"Update error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test())
