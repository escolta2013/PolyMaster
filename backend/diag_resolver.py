from app.core.config import settings
from supabase import create_client
from datetime import datetime, timezone

sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
now_iso = datetime.now(timezone.utc).isoformat()

res = sb.table("autonomous_logs").select("id, market_id, market_question, end_date_iso").eq("correct", "PENDING").eq("decision", "WOULD_EXECUTE").lt("end_date_iso", now_iso).order("end_date_iso", desc=False).limit(10).execute()
print(f"Con end_date vencida: {len(res.data)}")
for r in res.data:
    print(f"  id={r['id']} end={r['end_date_iso']} | {r['market_question'][:55]}")

res2 = sb.table("autonomous_logs").select("count", count="exact").eq("correct", "PENDING").eq("decision", "WOULD_EXECUTE").is_("end_date_iso", "null").execute()
print(f"\nCon end_date=NULL: {res2.count} trades")
