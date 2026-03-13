
import httpx
import json

def check_gamma_price():
    r = httpx.get('https://gamma-api.polymarket.com/markets?limit=1&active=true')
    m = r.json()[0]
    print(json.dumps(m, indent=2))

if __name__ == "__main__":
    check_gamma_price()
