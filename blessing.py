import time
from web3 import Web3

abi = """
[
    {
        "inputs": [{
            "internalType": "address",
            "name": "user",
            "type": "address"
        }],
        "name": "getActivationStatus",
        "outputs": [{
            "internalType": "bool",
            "name": "isLostStreak",
            "type": "bool"
        }, {
            "internalType": "bool",
            "name": "hasPrayedToday",
            "type": "bool"
        }],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{
            "internalType": "address",
            "name": "to",
            "type": "address"
        }],
        "name": "activateStreak",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]
"""

### ============方法定义 start =============
# 开始祈福
def start(private_key):
    # 合约地址: https://app.roninchain.com/address/ronin:9d3936dbd9a794ee31ef9f13814233d435bd806c
    blessing_contract_address='0x9d3936dbd9a794ee31ef9f13814233d435bd806c'
    ronin_rpc = 'https://api.roninchain.com/rpc'
    provider = Web3.HTTPProvider(ronin_rpc)
    w3 = Web3(provider)

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(blessing_contract_address), 
        abi=abi
    )

    signer = w3.eth.account.from_key(private_key)
    address = signer.address
    current = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
    if has_currently_activated(contract, address):
        print(f'[{current}] {address} 已祈福')
        return
    if activate_streak(w3, contract, signer):
        print(f'[{current}] {address} 祈福成功')
        return

# 检查当前账号是否已经祈福（不会消耗gas费）
def has_currently_activated(contract, address):
    result = contract.functions.getActivationStatus(address).call()
    isLostStreak, hasPrayedToday = result
    print(f'\n当前账号状态 {address}:')
    print(f'连续签到状态: {"已中断" if isLostStreak else "正常"}')
    print(f'今日祈福状态: {"已完成" if hasPrayedToday else "未完成"}')
    return hasPrayedToday  # 返回 hasPrayedToday 的值

# 向区块发送祈福请求（执行会消耗gas费）
def activate_streak(w3, contract, signer):
    try:
        transaction = contract.functions.activateStreak(signer.address).build_transaction({
            'chainId': 2020,
            'nonce': w3.eth.get_transaction_count(signer.address),
            'gasPrice': w3.to_wei('50', 'gwei')
        })
        signed_txn = signer.sign_transaction(transaction)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return True
    except Exception as e:
        print(f'祈福失败 {signer.address} - {e}')
        return False
### ============方法定义 end =============

### ============脚本执行 start =============

keys = [
        # "0xa2b6745bfbbbe80da68a02750a28c4131471edc5b3e4d857762e931564c7775b",
        # "0x728c163269ccbe8b067afacab4b61a5ddd97a74f73bedc8db59a2e6d4524a06a",
        "0x39bffa3f7879f7c3ac6c2675e4e5d865184e91e305037917355667dbcaf1af5e",
        "0xd5f45956a67b78e4d3054e8259f55cc5cb378231a292d09af5eba6dcf8bec49d"
        # "0x13fec1ae76d13b04f4f85860ceae6a3d7a3bf82dfba893d96da14fddf2252e8c",
        # "0x3237e0dd3c19f19a4c5efdab441e1213459bc191985a8406405298feca7a99c2"
]

# 遍历所有账号，挨个祈福
for key in keys:
  start(key)

### ============脚本执行 end =============