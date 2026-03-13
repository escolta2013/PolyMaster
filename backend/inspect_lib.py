import py_clob_client
import py_clob_client.clob_types
from py_clob_client.client import ClobClient

print("Py Clob Client Version:", getattr(py_clob_client, "__version__", "Unknown"))
print("ClobClient dir:", dir(ClobClient))
print("py_clob_client.clob_types dir:", dir(py_clob_client.clob_types))
