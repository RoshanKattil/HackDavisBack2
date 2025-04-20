from web3 import Web3
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
hex_len = len(w3.eth.get_code("0x5FbDB2315678afecb367f032d93F642f64180aa3"))
print("code length:", hex_len)
