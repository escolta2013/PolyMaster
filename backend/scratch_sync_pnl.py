import os
from supabase import create_client

from dotenv import load_dotenv
load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

if not url or not key:
    print("Error: Missing Supabase credentials in .env")
    exit(1)

sb = create_client(url, key)

# Sync win/loss into copy_trades
logs = sb.table('autonomous_logs').select('market_id, outcome, correct').neq('correct', 'PENDING').execute()
count = 0
for log in (logs.data or []):
    m_id = log['market_id']
    side = log['outcome']
    status = log['correct']
    
    # Update copy_trades
    trades = sb.table('copy_trades').select('id, shares').eq('market_id', m_id).eq('outcome', side).execute()
    for t in (trades.data or []):
        ov = float(t['shares']) if status == 'WIN' else 0.0
        sb.table('copy_trades').update({'outcome_value': ov}).eq('id', t['id']).execute()
        count += 1

print(f"Sincronización terminada: {count} registros de beneficios actualizados.")
