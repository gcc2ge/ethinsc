from dataclasses import dataclass
import hashlib
import time


@dataclass
class EthInscInfo:
    exist: bool
    ethscription_hex: str  # input data 编码后的数据


@dataclass
class IERC20Protocol:
    '''
    data:application/json,{"p":"ierc-20","op":"mint","tick":"𝕏","nonce":"1690983954805","amt":"1000"}
    '''

    prifix: str = 'data:application/json,'
    p: str = 'ierc-20'

    def mint(self, tick, amt):
        t = time.time()
        nonce = int(round(t * 1000))
        data = f'{self.prifix}{{"p":"{self.p}","op":"mint","tick":"{tick}","nonce":"{nonce}","amt":"{amt}"}}'
        hash = hashlib.sha256(data.encode('utf-8')).hexdigest()
        return hash, data


@dataclass
class IERC20POWProtocol:
    '''
    data:application/json,{"p":"ierc-20","op":"mint","tick":"𝕏","nonce":"1690983954805","amt":"1000"}
    '''

    prifix: str = 'data:application/json,'
    p: str = 'ierc-20'
    pow_nonce = 0

    def get_nonce(self):
        t = time.time()
        nonce = int(round(t * 1000000))
        target_nonce = f"{nonce}{self.pow_nonce}"
        self.pow_nonce = self.pow_nonce+1
        return target_nonce

    def mint(self, tick, amt):
        nonce = self.get_nonce()
        data = f'{self.prifix}{{"p":"{self.p}","op":"mint","tick":"{tick}","amt":"{amt}","nonce":"{nonce}"}}'
        hash = hashlib.sha256(data.encode('utf-8')).hexdigest()

        hex_representation = hex(int.from_bytes(data.encode(), 'big'))
        return hash, data, hex_representation


@dataclass
class ERC20Protocol:
    '''
    data:,{"p":"erc-20","op":"mint","tick":"pyusd","id":"2","amt":"1000"}
    '''

    # start: int
    # end: int

    prifix: str = 'data:,'
    p: str = 'erc-20'

    def mint(self, tick, amt):
        t = time.time()
        nonce = int(round(t * 1000))

        data = f'{self.prifix}{{"p":"{self.p}","op":"mint","tick":"{tick}","id":"{nonce}","amt":"{amt}"}}'
        hash = hashlib.sha256(data.encode('utf-8')).hexdigest()
        return hash, data
