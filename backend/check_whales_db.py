from app.core.config import settings
from supabase import create_client, Client
import asyncio
import os

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

resp = supabase.table("wallets").select("address, grade").eq("is_smart_money", True).execute()
print(f"Total smart wallets in DB: {len(resp.data)}")
for w in resp.data:
    print(w)
