"""Async entity management module for Arkiv client."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from eth_typing import HexStr
from web3.types import TxParams, TxReceipt

from .module_base import ArkivModuleBase
from .types import Operations, TransactionReceipt, TxHash
from .utils import to_receipt, to_tx_params

# Deal with potential circular imports between client.py and module_async.py
if TYPE_CHECKING:
    from .client import AsyncArkiv

logger = logging.getLogger(__name__)

TX_SUCCESS = 1


class AsyncArkivModule(ArkivModuleBase["AsyncArkiv"]):
    """Async Arkiv module for entity management operations."""

    async def execute(
        self, operations: Operations, tx_params: TxParams | None = None
    ) -> TransactionReceipt:
        """
        Execute operations on the Arkiv storage contract (async).

        Args:
            operations: Operations to execute (creates, updates, deletes, extensions)
            tx_params: Optional additional transaction parameters

        Returns:
            TransactionReceipt with details of all operations executed
        """
        # Convert to transaction parameters and send
        client: AsyncArkiv = self.client
        tx_params = to_tx_params(operations, tx_params)
        tx_hash_bytes = await client.eth.send_transaction(tx_params)
        tx_hash = TxHash(HexStr(tx_hash_bytes.to_0x_hex()))

        tx_receipt: TxReceipt = await client.eth.wait_for_transaction_receipt(tx_hash)
        tx_status: int = tx_receipt["status"]
        if tx_status != TX_SUCCESS:
            raise RuntimeError(f"Transaction failed with status {tx_status}")

        # Parse and return receipt
        receipt: TransactionReceipt = to_receipt(
            client.arkiv.contract, tx_hash, tx_receipt
        )
        logger.debug(f"Arkiv receipt: {receipt}")
        return receipt
