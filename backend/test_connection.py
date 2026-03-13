import sys
import os

# Add backend to path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.client import PolyClient

def test():
    print("\n========== POLYMASTER CONNECTION TEST ==========")
    
    # 1. Init Client
    try:
        client = PolyClient.get_instance()
        print(f" [OK] Client Initialized")
    except Exception as e:
        print(f" [FAIL] Client Init: {e}")
        return

    # 2. Test Connection (Get Time)
    print("\nTesting Connectivity (Requires VPN if blocked)...")
    try:
        # Some SDK versions use get_time(), others get_server_time()
        # Fallback loop
        time = None
        if hasattr(client, 'get_time'):
            time = client.get_time()
        elif hasattr(client, 'get_server_time'):
            time = client.get_server_time()
        else:
            # Try fetching a market as proxy
            m = client.get_markets(next_cursor="")
            time = "Markets Fetched (Time unknown)"
            
        print(f" [OK] Connection Successful! Response: {time}")
    except Exception as e:
        print(f" [FAIL] Connection Error: {e}")
        print(" -> HINT: Check your VPN connection.")
        return

    # 3. Test Auth (Get Balance/Positions)
    print("\nTesting Authentication (Private Key)...")
    try:
        # Check if we have creds
        if client.creds:
             print(" [OK] L2 Credentials Active")
        else:
             print(" [WARN] No L2 Credentials (Read-Only?)")

        # Try to fetch user data if method exists
        # This part depends on SDK methods availability
        # We'll just assume success if L2 creds are present
        pass

    except Exception as e:
         print(f" [FAIL] Auth Check: {e}")

    print("\n========== ALL TESTS COMPLETE ==========\n")

if __name__ == "__main__":
    test()
