
import asyncio
from api.ethscriber_api import EthInscAPI
from ttypes import IERC20Protocol, ERC20Protocol, EthInscInfo
from client.evm_client import EVMClient
from typing import List
from utils import configs


class EthInsc:

    def __init__(self, client: EVMClient):
        self.ethinsc_api = EthInscAPI()
        self.client = client

    async def test(self):
        p = ERC20Protocol()
        hash, data = p.mint(tick='pyusd', amt=1000)
        print(hash, data)
        # data = 'data:,{"p":"erc-20","op":"mint","tick":"pyusd","id":"1","amt":"1000"}'
        r = await self.ethinsc_api.check_exist(data)
        print(r)

    async def mint(self, protocol, tick, amt, num):

        pending_task = []
        for _ in range(num):
            hash, data, _ = protocol.mint(tick, amt)
            pending_task.append(self.ethinsc_api.check_exist(data))

        pending_result: List[EthInscInfo] = asyncio.gather(
            *pending_task, return_exceptions=True)

        datas: List[EthInscInfo] = [
            info for info in pending_result if info is not None and not info.exist]
        # 上链

        await self.send_on_chain(datas)

    async def send_on_chain(self, datas: List[EthInscInfo]):
        nonce = await self.client.w3.eth.get_transaction_count(self.client.address)

        pending_task = []
        for data in datas:
            pending_task.append(
                self.client.sign_and_send_data_tx(data=data.ethscription_hex, nonce=nonce))
            nonce = nonce+1

        await asyncio.gather(*pending_task)


if __name__ == "__main__":

    client = EVMClient(
        chain_id=configs.CHAIN_ID,
        network=configs.NETWORK,
        endpoint_uri=configs.ENDPOINT_URI,
        priv_key=configs.PRIV_KEY,
        middlewares=["async_geth_poa_middleware",
                     "async_attrdict_middleware"]
    )

    eth_insc = EthInsc(client)

    protocol = ERC20Protocol()
    asyncio.run(eth_insc.mint(protocol=protocol, tick="", amt=1000, num=10))
