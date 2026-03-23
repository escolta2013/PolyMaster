from app.core.config import settings
from supabase import create_client
from datetime import datetime, timezone, timedelta

sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

# Fetch recent entries
res = sb.table("autonomous_logs").select("id, market_question, decision, correct, end_date_iso, detected_at, confidence, spread").gte("detected_at", since).order("detected_at", desc=True).limit(50).execute()

data = res.data
execs = [r for r in data if r.get("decision") == "WOULD_EXECUTE"]
skips = [r for r in data if r.get("decision") == "SKIP"]

print(f"Latest 50 entries in 24h window (Processed total: {len(data)})")
print(f"WOULD_EXECUTE: {len(execs)} | SKIP: {len(skips)}")

print("\nRecent Execute (last 10):")
for r in execs[:10]:
    id_val = r.get("id")
    status = r.get("correct")
    question = str(r.get("market_question"))[:60]
    dt = r.get("detected_at")[:16].replace("T", " ")
    print(f"[{dt}] ID {id_val} | Status: {status:8} | {question}")

print("\nRecent Skips (last 10):")
for r in skips[:10]:
    id_val = r.get("id")
    conf = r.get("confidence")
    spread = r.get("spread")
    question = str(r.get("market_question"))[:60]
    dt = r.get("detected_at")[:16].replace("T", " ")
    print(f"[{dt}] ID {id_val} | Conf: {conf:5} | Spread: {spread:5} | {question}")
