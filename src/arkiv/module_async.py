"""Async entity management module for Arkiv client."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from eth_typing import HexStr
from web3.types import TxParams, TxReceipt

from .module_base import ArkivModuleBase
from .types import (
    Annotations,
    CreateOp,
    EntityKey,
    Operations,
    TransactionReceipt,
    TxHash,
)
from .utils import to_tx_params

# Deal with potential circular imports between client.py and module_async.py
if TYPE_CHECKING:
    from .client import AsyncArkiv  # noqa: F401 - used in Generic type parameter

logger = logging.getLogger(__name__)


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
        tx_params = to_tx_params(operations, tx_params)

        # Send transaction and get tx hash
        tx_hash_bytes = await self.client.eth.send_transaction(tx_params)
        tx_hash = TxHash(HexStr(tx_hash_bytes.to_0x_hex()))

        # Wait for transaction to complete and return receipt
        tx_receipt: TxReceipt = await self.client.eth.wait_for_transaction_receipt(
            tx_hash
        )
        return self._check_tx_and_get_receipt(tx_hash, tx_receipt)

    async def create_entity(
        self,
        payload: bytes | None = None,
        annotations: Annotations | None = None,
        btl: int | None = None,
        tx_params: TxParams | None = None,
    ) -> tuple[EntityKey, TxHash]:
        """
        Create a new entity on the Arkiv storage contract (async).

        Args:
            payload: Optional data payload for the entity
            annotations: Optional key-value annotations
            btl: Blocks to live (default: self.btl_default, ~30 minutes with 2s blocks)
            tx_params: Optional additional transaction parameters

        Returns:
            The entity key and transaction hash of the create operation
        """
        # Create the operation
        payload, annotations, btl = self._check_and_set_argument_defaults(
            payload, annotations, btl
        )
        create_op = CreateOp(payload=payload, annotations=annotations, btl=btl)

        # Wrap in Operations container and execute
        operations = Operations(creates=[create_op])
        receipt = await self.execute(operations, tx_params)

        # Verify we got at least one create
        creates = receipt.creates
        if len(creates) != 1:
            raise RuntimeError(
                f"Receipt should have exactly one entry in 'creates' but got {len(creates)}"
            )

        create = creates[0]
        entity_key = create.entity_key
        return entity_key, receipt.tx_hash
