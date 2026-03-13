
from app.core.config import settings
from supabase import create_client
from datetime import datetime
import json

def check_supabase():
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    # Check logs
    try:
        logs = supabase.table("autonomous_logs").select("*").limit(10).order("detected_at", desc=True).execute()
        print("--- LATEST AUTONOMOUS LOGS ---")
        for log in logs.data:
            print(f"[{log.get('detected_at')}] {log.get('market_id', '')[:10]}... | {log.get('decision', 'N/A')} | Score: {log.get('council_score')} | Reason: {log.get('reasoning', '')[:50]}...")
    except Exception as e:
        print(f"Error reading autonomous_logs: {e}")
        
    # Check whale alerts
    try:
        alerts = supabase.table("cluster_alerts").select("*").limit(5).order("created_at", desc=True).execute()
        print("\n--- LATEST CLUSTER ALERTS ---")
        for alert in alerts.data:
            print(f"[{alert['created_at']}] {alert['market_id'][:10]}... | {alert.get('market_question', 'N/A')[:40]}...")
    except Exception as e:
        print(f"Error reading cluster_alerts: {e}")

if __name__ == "__main__":
    check_supabase()
