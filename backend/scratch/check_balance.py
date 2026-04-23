from eth_account import Account
from web3 import Web3
import os

# USDC on Polygon
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174" # USDC.e
USDC_ABI = [{"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}]

PK = "8a1b654d3b43e22daebda4ab0c7b66a9b906808e8a1e115e22d50356dc1ac66e"
PROXY = "0xEC812165668F4C339405b8E54C9c6B18432171cE"
RPC = "https://polygon-rpc.com/"

def check():
    w3 = Web3(Web3.HTTPProvider(RPC))
    acct = Account.from_key(PK)
    print(f"MAIN WALLET ADDRESS: {acct.address}")
    print(f"PROXY WALLET ADDRESS: {PROXY}")
    
    usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_ADDRESS), abi=USDC_ABI)
    
    main_bal = usdc.functions.balanceOf(acct.address).call() / 10**6
    proxy_bal = usdc.functions.balanceOf(Web3.to_checksum_address(PROXY)).call() / 10**6
    
    print(f"MAIN BALANCE: ${main_bal}")
    print(f"PROXY BALANCE: ${proxy_bal}")

if __name__ == "__main__":
    check()
