import requests
import json

tid = "30849748446697835087456624677708330354045483976550757302450375628468725832168"
url = f"https://clob.polymarket.com/book?token_id={tid}"
r = requests.get(url)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    ob = r.json()
    asks = ob.get("asks", [])
    bids = ob.get("bids", [])
    if asks and bids:
        ask = float(asks[0]["price"])
        bid = float(bids[0]["price"])
        print(f"P: {(ask+bid)/2:.3f} | S: {ask-bid:.3f}")
    else:
        print("No liquidity")
else:
    print(r.text)
