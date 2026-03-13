
import os, sys, httpx, asyncio, json
from typing import Optional, List, Dict
from dotenv import load_dotenv

# Load environment
load_dotenv()
sys.path.insert(0, os.path.abspath("."))

from app.core.config import settings
from supabase import create_client

async def fetch_market_status(client: httpx.AsyncClient, market_id: str) -> Dict:
    """Fetch market resolution status from Gamma API."""
    try:
        url = f"https://gamma-api.polymarket.com/markets/{market_id}"
        resp = await client.get(url, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "resolved": data.get("closed", False),
                "best_ask": data.get("bestAsk"),
                "best_bid": data.get("bestBid")
            }
    except Exception as e:
        pass
    return {}

async def backfill_correctness():
    print("Iniciando backfill de la columna 'correct' en Supabase...")
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    # Obtener registros de WOULD_EXECUTE que no tienen 'correct' (o todos para refrescar)
    res = supabase.table("autonomous_logs").select("id, market_id, outcome").eq("decision", "WOULD_EXECUTE").execute()
    rows = res.data or []
    print(f"Encontrados {len(rows)} registros para verificar.")

    async with httpx.AsyncClient() as client:
        batch_size = 20
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            
            for row in batch:
                status = await fetch_market_status(client, row["market_id"])
                best_ask = status.get("best_ask")
                
                if best_ask is None:
                    continue
                
                # Lógica de resolución:
                # Si el bot apostó YES (compró YES token)
                # WIN si best_ask >= 0.98 (token vale $1)
                # LOSS si best_ask <= 0.02 (token vale $0)
                
                correct_str = "PENDING"
                if float(best_ask) >= 0.98:
                    correct_str = "WIN"
                elif float(best_ask) <= 0.02:
                    correct_str = "LOSS"
                
                # Actualizar en Supabase
                supabase.table("autonomous_logs").update({"correct": correct_str}).eq("id", row["id"]).execute()
            
            print(f"Procesados {min(i + batch_size, len(rows))}/{len(rows)}...")

    print("Backfill completado.")

if __name__ == "__main__":
    asyncio.run(backfill_correctness())
