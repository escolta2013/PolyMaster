import random
import requests
from datetime import datetime
from app.core.client import PolyClient

class MarketScanner:
    def __init__(self):
        self.client = PolyClient.get_instance()
        self.gamma_url = "https://gamma-api.polymarket.com/markets"
        self._price_cache = {} # token_id -> price

    def scan_hype_spikes(self):
        """
        Scans for 'Hype Spikes' using Gamma API for metadata + CLOB for live prices.
        """
        try:
            # 1. Fetch active, high-volume markets from Gamma
            params = {
                "active": "true",
                "closed": "false",
                "order": "volume",
                "ascending": "false",
                "limit": 20
            }
            resp = requests.get(self.gamma_url, params=params)
            resp.raise_for_status()
            raw_markets = resp.json()
            
            results = []
            for m in raw_markets:
                try:
                    # Gamma API stores question/ID in dict keys
                    question = m.get('question', 'Unknown Market')
                    market_id = m.get('conditionId', '0x')
                    
                    # Gamma response has 'clobTokenIds' or similar
                    # For simplified price check, we need the token ID
                    clob_tokens = m.get('clobTokenIds')
                    if not clob_tokens or not isinstance(clob_tokens, list):
                        continue
                    
                    # Assume first token is 'YES' for spike analysis
                    token_id_str = clob_tokens[0].strip('[]" ')
                    
                    # Fetch Live Midpoint Price from CLOB
                    try:
                        mid_data = self.client.get_midpoint(token_id_str)
                        price = float(mid_data.get('mid', 0.5))
                    except:
                        # Fallback to Gamma's last price if CLOB fails
                        price = float(m.get('lastTradePrice', 0.5))
                    
                    # Trend Detection: Compare with cache
                    prev_price = self._price_cache.get(token_id_str, price)
                    change = price - prev_price
                    self._price_cache[token_id_str] = price # Update cache
                    
                    # Calculate Spike Magnitude (Real trend or deviation)
                    spike_mag = abs(change) * 15.0 + abs(price - 0.5) * 0.1
                    spike_mag = min(spike_mag + (random.random() * 0.05), 1.0)

                    # Liquidity Scoring (Gamma usually has 'liquidity' or we use volume)
                    vol_24h = float(m.get('volume24hr', 0))
                    liquidity_score = min(vol_24h / 10000, 95) + 5 # Heuristic
                    
                    # Logic to determine "Reason"
                    reason = "Momentum Shift" if abs(change) > 0.01 else "High Volume"
                    if vol_24h > 500000: reason = "Institutional Flow"
                    if price > 0.9: reason = "Cashing Out"
                    
                    results.append({
                        "id": market_id,
                        "question": question,
                        "spike_magnitude": round(spike_mag, 3),
                        "liquidity_score": round(liquidity_score, 1),
                        "price": round(price, 3),
                        "reason": reason,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                except Exception as e:
                    # print(f"Skipping market: {e}")
                    continue
            
            # Sort by spike magnitude
            results.sort(key=lambda x: x['spike_magnitude'], reverse=True)
            return results

        except Exception as e:
            print(f"Scanner Error: {e}")
            return []
