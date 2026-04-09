
import os
from eth_account import Account
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# RPCs
RPCS = [
    "https://polygon-rpc.com",
    "https://1rpc.io/matic",
    "https://polygon.llamarpc.com"
]

PK = os.getenv("PK")
PROXY = os.getenv("POLY_PROXY_ADDRESS")

def check():
    if not PK:
        print("Error: No PK found in .env")
        return

    acc = Account.from_key(PK)
    addr = PROXY if PROXY else acc.address
    print(f"Checking address: {addr}")

    w3 = None
    for url in RPCS:
        try:
            temp_w3 = Web3(Web3.HTTPProvider(url))
            if temp_w3.is_connected():
                w3 = temp_w3
                print(f"Connected to {url}")
                break
        except:
            continue

    if not w3:
        print("Failed to connect to any RPC")
        return

    # 1. Native MATIC (POL)
    matic_bal = w3.eth.get_balance(addr)
    print(f"MATIC Balance: {w3.from_wei(matic_bal, 'ether')} POL")

    # 2. USDC
    USDC_ADDRESS = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
    USDC_ABI = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
    
    usdc_contract = w3.eth.contract(address=w3.to_checksum_address(USDC_ADDRESS), abi=USDC_ABI)
    usdc_bal = usdc_contract.functions.balanceOf(addr).call()
    print(f"USDC Balance: {usdc_bal / 1e6} USDC")

if __name__ == "__main__":
    check()
