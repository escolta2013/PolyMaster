import asyncio
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, BalanceAllowanceParams, AssetType

def test_auth():
    pk = '0x28c39004381b8aa5c78f2fa54c7abd1b55b0d3ce6c2cb9b91c4c1267a78bc5ed'
    host = 'https://clob.polymarket.com'
    chain_id = 137
    
    clob_key = '019d6576-02fe-7d3d-a67a-a888023b8988'
    clob_sec = 'jRfUdEpWXAb7_oNPckku4MHBnxRQsl7pSNZK1WXh-AA='
    clob_pass = '4df65f1035e32e57b4f1229441b75c4c69f1a2a142a36a1ad75372bac74928ec'
    creds = ApiCreds(clob_key, clob_sec, clob_pass)

    c_temp = ClobClient(host=host, key=pk, chain_id=chain_id)
    try:
        funder = c_temp.derive_proxy_address() # if this exists? Nope, I don't know the exact function name
    except:
        funder = None

    # Let's get the proxy for 0xaeb06e556Cc995Dd44986dCA000433Cb624c0872
    # Typically we can query proxy via ClobClient... wait, let's look at ClobClient's builder?
    pass

test_auth()
