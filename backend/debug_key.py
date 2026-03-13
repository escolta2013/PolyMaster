import os
import re
from dotenv import load_dotenv

load_dotenv()

def check_key(name):
    val = os.getenv(name)
    if not val:
        print(f"[{name}] MISSING or EMPTY")
        return

    print(f"[{name}]")
    print(f"  Length: {len(val)}")
    
    # Check for quotes
    if val.startswith('"') or val.startswith("'"):
        print("  WARNING: Starts with quote! .env parsing might be issue.")
    
    # Check hex
    is_hex = True
    try:
        int(val, 16)
    except:
        is_hex = False
    
    print(f"  Is Valid Hex? {is_hex}")
    print(f"  Starts with 0x? {val.startswith('0x')}")
    
    # Check for non-printable chars (whitespace)
    if re.search(r'\s', val):
        print("  WARNING: Contains whitespace/newlines!")
    else:
        print("  Clean (no whitespace)")

check_key("POLYMARKET_PRIVATE_KEY")
check_key("POLYMARKET_API_KEY")
check_key("POLYMARKET_SECRET")
# Passphrase often not hex, so skipping hex check for it strictly?
# But checking anyway.
check_key("POLYMARKET_PASSPHRASE")
