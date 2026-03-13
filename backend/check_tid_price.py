import requests
import json

tids = [
    "108243474329505357331058907696165808979046872934342185786419726202568603611394",
    "40417978160073212871239695624177579679632833075675565509204481001479860471842"
]

for tid in tids:
    url = f"https://clob.polymarket.com/book?token_id={tid}"
    r = requests.get(url)
    if r.status_code == 200:
        ob = r.json()
        asks = ob.get("asks", [])
        bids = ob.get("bids", [])
        if asks and bids:
            ask = float(asks[0]["price"])
            bid = float(bids[0]["price"])
            print(f"[{tid}] Price: {(ask+bid)/2:.3f} | Spread: {ask-bid:.3f}")
        else:
            print(f"[{tid}] No liquidity")
    else:
        print(f"[{tid}] Error {r.status_code}")
