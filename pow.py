

from eth_account.datastructures import SignedTransaction

from typing import Tuple

import asyncio
from api.ethscriber_api import EthInscAPI
from ttypes import IERC20POWProtocol, EthInscInfo
from client.evm_client import EVMClient
from utils import configs


class POWInscription:
    def __init__(self, client: EVMClient, workc="0x00000"):

        self.workc = workc

        self.ethinsc_api = EthInscAPI()
        self.client = client

    async def mint(self, protocol: IERC20POWProtocol, tick, amt, num):
        '''
        num 最多循环几次
        '''
        nonce = await self.client.w3.eth.get_transaction_count(self.client.address)
        print(self.client.address, nonce)

        for _ in range(num):
            hash, data, hex_representation = protocol.mint(tick, amt)
            tx_hash, signed_tx = await self.client.sign_data_tx(data=hex_representation, nonce=nonce)
            print(tx_hash)
            if tx_hash.startswith(self.workc):
                info: EthInscInfo = await self.ethinsc_api.check_exist(data)
                if info is not None and not info.exist:
                    print(info.ethscription_hex)
                    while True:
                        try:
                            await self.client.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                            break
                        except:
                            continue

                    break


if __name__ == "__main__":

    client = EVMClient(
        chain_id=configs.CHAIN_ID,
        network=configs.NETWORK,
        endpoint_uri=configs.ENDPOINT_URI,
        priv_key=configs.PRIV_KEY,
        eip_1559=False,
        middlewares=["async_geth_poa_middleware",
                     "async_attrdict_middleware"]
    )

    eth_insc = POWInscription(client, workc="0x0000000")

    protocol = IERC20POWProtocol()
    asyncio.run(eth_insc.mint(protocol=protocol,
                tick="ierc-m7", amt=1000, num=100000000000000000000000000000000000000))
