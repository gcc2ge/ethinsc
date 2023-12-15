

from copy import copy

import web3.middleware
from eth_account.datastructures import SignedTransaction
from eth_account.signers.local import LocalAccount
from web3 import Account, AsyncHTTPProvider, AsyncWeb3
from aiocache import cached
from web3.contract.async_contract import AsyncContractFunction
from web3.types import TxParams
from typing import Tuple

DEFAULT_CONN_TIMEOUT = 3
MAX_BLOCKS_WAIT_RECEIPT = 10
DEFAULT_MAX_GAS = 1_000_000
DEFAULT_GAS_MULTIPLIER = 1.01
DEFAULT_BASE_FEE_MULTIPLIER = 1.01


class EVMClient:
    def __init__(
        self,
        endpoint_uri: str,
        chain_id: int,
        network: str,
        priv_key: str,
        middlewares: list[str] = None,
        timeout: int = None,
        block_identifier="latest",
        eip_1559: bool = True,
        base_fee_change_denominator=8,
        elasticity_multiplier=2,
        gas_multiplier: float = DEFAULT_GAS_MULTIPLIER,
        base_fee_multiplier: float = DEFAULT_BASE_FEE_MULTIPLIER,
    ):
        self.endpoint_uri = endpoint_uri
        self.chain_id = chain_id
        self.network = network
        self.middlewares = middlewares
        self.timeout = DEFAULT_CONN_TIMEOUT if timeout is None else timeout
        self.block_identifier = block_identifier
        self.eip_1559 = eip_1559
        self.base_fee_change_denominator = base_fee_change_denominator
        self.elasticity_multiplier = elasticity_multiplier
        self.gas_multiplier = gas_multiplier
        self.base_fee_multiplier = base_fee_multiplier

        self.w3 = get_w3(endpoint_uri, middlewares, timeout)
        # self.height = self.w3.eth.block_number

        self.account: LocalAccount = Account.from_key(priv_key)
        self.address: str = self.account.address

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(endpoint_uri={self.endpoint_uri}, address={self.address})"
        )

    def next_base_fee(self,
                      parent_block,
                      # limits the maximum base fee increase per block to 1/8 (12.5%)
                      base_fee_change_denominator=8,
                      elasticity_multiplier=2):
        """
        Calculate next base fee for an EIP-1559 compatible blockchain. The
        formula is taken from the example code in the EIP-1559 proposal (ref:
        https://eips.ethereum.org/EIPS/eip-1559).

        The default values for `base_fee_max_change_denominator` and
        `elasticity_multiplier` are taken from EIP-1559.

        Enforces `min_base_fee` if provided.
        """
        # parent_block = await self.w3.eth.get_block('latest')
        parent_block = dict(parent_block)
        parent_bas_fee = parent_block["baseFeePerGas"]
        parent_gas_used = parent_block["gasUsed"]
        parent_gas_target = parent_block["gasLimit"] / elasticity_multiplier

        if parent_gas_used == parent_gas_target:
            base_fee = parent_bas_fee
        elif parent_gas_used > parent_gas_target:
            gas_used_delta = parent_gas_used - parent_gas_target
            base_fee_delta = max(parent_bas_fee * gas_used_delta //
                                 parent_gas_target // base_fee_change_denominator, 1)
            base_fee = parent_bas_fee + base_fee_delta
        else:
            gas_used_delta = parent_gas_target - parent_gas_used
            base_fee_delta = parent_bas_fee * \
                gas_used_delta // parent_gas_target // base_fee_change_denominator
            base_fee = parent_bas_fee - base_fee_delta
        return base_fee

    @cached(ttl=3600)
    async def get_gas_price(
        self,
        gas_multiplier: float = None,
        base_fee_multiplier: float = None,
        force_legacy_tx: bool = False,
    ) -> dict[str, int]:
        gas_multiplier = gas_multiplier or self.gas_multiplier
        base_fee_multiplier = self.base_fee_multiplier if base_fee_multiplier is None else base_fee_multiplier

        if force_legacy_tx or not self.eip_1559:
            return {"gasPrice": round(int(await self.w3.eth.gas_price) * gas_multiplier)}
        else:
            # pending_block, max_priority_fee = await asyncio.gather(self.w3.eth.get_block("pending"), self.w3.eth.max_priority_fee)
            # base_fee = pending_block["baseFeePerGas"]

            # parent_block, max_priority_fee = await asyncio.gather(self.w3.eth.get_block("latest"), self.w3.eth.max_priority_fee)
            parent_block, max_priority_fee = await self.w3.eth.get_block("latest"), self.w3.to_wei(0.1, 'gwei'),
            base_fee = self.next_base_fee(parent_block)
            return {
                "maxFeePerGas": int(base_fee * base_fee_multiplier)+int(max_priority_fee * gas_multiplier),
                "maxPriorityFeePerGas": int(max_priority_fee * gas_multiplier),
                "type": 2,
            }

    async def sign_and_send_tx(self, tx: TxParams, gas_multiplier: int = None, force_legacy_tx: bool = False,) -> str:
        tx = copy(tx)
        tx.setdefault("gas", DEFAULT_MAX_GAS)

        # Avoid dict's setdefault() or get() to avoid side effects / calling expensive functions
        if "nonce" not in tx:
            tx["nonce"] = await self.w3.eth.get_transaction_count(self.address)
        if "gasPrice" not in tx or self.eip_1559 and "maxFeePerGas" not in tx:
            tx.update(await self.get_gas_price(
                gas_multiplier=gas_multiplier,
                force_legacy_tx=force_legacy_tx))  # type: ignore

        signed_tx: SignedTransaction = self.account.sign_transaction(tx)
        tx_hash = signed_tx.hash.hex()

        print(f"Sending transaction {tx_hash}: {tx}")
        tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash.hex()

    async def sign_and_send_data_tx(
        self,
        data: str,
        value: int = 0,
        max_gas: int = None,
        gas_multiplier: float = None,
        base_fee_multiplier: float = None,
        force_legacy_tx: bool = False,
        nonce=None,
    ) -> str:
        tx_params = {
            "from": self.address,
            "to": self.address,
            "value": value,
            "chainId": self.chain_id,
            "gas": DEFAULT_MAX_GAS if max_gas is None else max_gas,
            "nonce": nonce,
            "data": data,
            ** await self.get_gas_price(gas_multiplier=gas_multiplier, base_fee_multiplier=base_fee_multiplier, force_legacy_tx=force_legacy_tx),
        }
        tx = TxParams(**tx_params)
        return await self.sign_and_send_tx(tx, gas_multiplier=gas_multiplier, force_legacy_tx=force_legacy_tx)

    async def sign_data_tx(
        self,
        data: str,
        value: int = 0,
        max_gas: int = None,
        gas_multiplier: float = None,
        base_fee_multiplier: float = None,
        force_legacy_tx: bool = False,
        nonce=None,
    ) -> Tuple[str, SignedTransaction]:
        tx_params = {
            "from": self.address,
            "to": '0x0000000000000000000000000000000000000000',
            "value": value,
            "chainId": self.chain_id,
            "gas": DEFAULT_MAX_GAS if max_gas is None else max_gas,
            "nonce": nonce,
            "data": data,
            ** await self.get_gas_price(gas_multiplier=gas_multiplier, base_fee_multiplier=base_fee_multiplier, force_legacy_tx=force_legacy_tx),
        }
        tx = TxParams(**tx_params)

        tx.setdefault("gas", DEFAULT_MAX_GAS)

        # Avoid dict's setdefault() or get() to avoid side effects / calling expensive functions
        if "nonce" not in tx:
            tx["nonce"] = await self.w3.eth.get_transaction_count(self.address)
        if "gasPrice" not in tx or self.eip_1559 and "maxFeePerGas" not in tx:
            tx.update(await self.get_gas_price(
                gas_multiplier=gas_multiplier,
                force_legacy_tx=force_legacy_tx))  # type: ignore

        signed_tx: SignedTransaction = self.account.sign_transaction(tx)
        tx_hash = signed_tx.hash.hex()

        return tx_hash, signed_tx


def get_w3(
    endpoint_uri: str,
    middlewares: list[str] = None,
    timeout: int = None,
) -> AsyncWeb3:
    timeout = DEFAULT_CONN_TIMEOUT if timeout is None else timeout
    if endpoint_uri.startswith("http"):
        provider = AsyncHTTPProvider(
            endpoint_uri, request_kwargs={"timeout": timeout})
    else:
        raise ValueError(f"Invalid {endpoint_uri=}")

    if middlewares is None:
        middlewares = []
    else:
        middlewares = [getattr(web3.middleware, m) for m in middlewares if m]
    return AsyncWeb3(provider, middlewares)
