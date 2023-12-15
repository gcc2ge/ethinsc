from ttypes import EthInscInfo
import httpx
import hashlib

class EthInscAPI:

    async def check_exist(self, data) -> EthInscInfo:
        # 将data转为hash
        hash = hashlib.sha256(data.encode('utf-8')).hexdigest()

        url = f"https://ethscriber.xyz/api/ethscriptions/exists/{hash}"

        async with httpx.AsyncClient(timeout=3000) as client:  # 创建一个异步client
            response = await client.get(url)

        if response.status_code == 200:
            result = response.json()
            if result["result"]:
                # 若已经存在的不想打印的话，直接注释掉下面这行
                print(f"{data} 已经存在")
                return EthInscInfo(exist=True, ethscription_hex=result['ethscription']['sha'])
            else:
                print(f"{data} 不存在，可以打，赶紧的")
                hex_representation = hex(int.from_bytes(data.encode(), 'big'))
                return EthInscInfo(exist=False, ethscription_hex=hex_representation)
        else:
            print(
                f"Failed to get messages. Status code: {response.status_code}")
            return None
