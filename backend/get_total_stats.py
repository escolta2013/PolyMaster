
import os, sys
from typing import Set

sys.path.insert(0, os.path.abspath("."))
from app.core.config import settings
from supabase import create_client

def get_stats():
    s = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    total_unique = set()
    offset = 0
    limit = 1000
    
    print("Fetching distinct market IDs from Supabase...")
    while True:
        res = s.table('autonomous_logs').select('market_id').range(offset, offset + limit - 1).execute()
        data = res.data
        if not data:
            break
        for d in data:
            if d.get('market_id'):
                total_unique.add(d['market_id'])
        
        print(f"Read {offset + len(data)} rows, {len(total_unique)} unique markets found...")
        if len(data) < limit:
            break
        offset += limit
        
    print(f"\nFINAL TOTAL UNIQUE MARKETS ANALYZED: {len(total_unique)}")

    # Break down by decision
    decisions = ["WOULD_EXECUTE", "REJECTED", "PAPER_REJECTED", "EXECUTED"]
    for dec in decisions:
        unique_dec = set()
        off = 0
        while True:
            r = s.table('autonomous_logs').select('market_id').eq('decision', dec).range(off, off + limit - 1).execute()
            d = r.data
            if not d: break
            for item in d: unique_dec.add(item['market_id'])
            if len(d) < limit: break
            off += limit
        print(f" - {dec:<15}: {len(unique_dec)} unique markets")

if __name__ == "__main__":
    get_stats()
